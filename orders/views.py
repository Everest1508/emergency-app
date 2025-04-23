from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from authapi.models import User
from orders.models import CustomerRequest, CustomerRequestDriverMapping
from utils.models import ApplicationSettings
from .serializers import CustomerRequestSerializer
import redis
from django.conf import settings
from utils.response import data_response
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from utils.notifications import send_expo_notification

redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

class CustomerCarRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        if user.user_type != 'customer':
            return Response(
                data_response(403, "Only customers can request a car.", {}),
                status=status.HTTP_403_FORBIDDEN
            )

        # Fetch application settings
        app_settings = ApplicationSettings.objects.first()
        max_requests = app_settings.maximum_requests_per_user if app_settings else 1

        # Check if user has exceeded max requests
        active_requests = CustomerRequest.objects.filter(customer=user, status__in=["pending", "in_progress"]).count()
        if active_requests >= max_requests:
            return Response(
                data_response(400, f"You can only have {max_requests} active requests.", {}),
                status=status.HTTP_400_BAD_REQUEST
            )

        data = request.data.copy()
        data["customer"] = user.id
        
        serializer = CustomerRequestSerializer(data=data)

        if serializer.is_valid():
            car_request = serializer.save()
            self.send_request_to_nearby_drivers(car_request, app_settings)
            return Response(
                data_response(201, "Car request created successfully", serializer.data),
                status=status.HTTP_201_CREATED
            )
        
        error_list = [
            f"{field.replace('_', ' ').capitalize()} is required." if error == "This field is required."
            else error
            for field, errors in serializer.errors.items()
            for error in errors
        ]

        return Response(
            data_response(400, "Bad Request", {"errors": error_list}),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    def send_request_to_nearby_drivers(self, car_request, app_settings):
        """
        Finds nearby drivers based on settings and sends WebSocket event.
        Also, stores the request-driver mapping for future updates.
        """
        latitude = car_request.latitude
        longitude = car_request.longitude
        request_type = car_request.request_type
        radius_km = app_settings.search_radius if app_settings else 10  
        send_request_to = app_settings.send_request_to if app_settings else 'all'

        nearby_drivers = redis_client.georadius(
            "drivers_locations", float(longitude), float(latitude),
            radius_km, unit="km", withcoord=False
        )

        channel_layer = get_channel_layer()
        request_type_dict = dict(CustomerRequest.REQUEST_TYPES)
        request_type_name = request_type_dict.get(request_type, "Unknown")
        fcm_tokens = []

        for driver_username in nearby_drivers:
            try:
                driver = User.objects.get(username=driver_username)
                if send_request_to == 'type' and driver.car_type != car_request.car_type:
                    continue
                if driver.device_id:
                    fcm_tokens.append(driver.device_id)
                    
                CustomerRequestDriverMapping.objects.create(request=car_request, driver=driver)
            except User.DoesNotExist:
                continue

            async_to_sync(channel_layer.group_send)(
                f"user_{driver_username}",
                {
                    "type": "new_booking_event",
                    "event": "new",
                    "id": car_request.id,
                    "booking_type": "booking",
                    "data": {
                        "user": {"name": car_request.customer.get_full_name(), "phone": str(car_request.customer.phone_number)},
                        "request_type": request_type_name, 
                        "location": {"lat": float(latitude), "lon": float(longitude)},
                        "status": car_request.status,
                        "timestamp": car_request.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "additional_details": car_request.additional_details or "",
                    },
                },
            )
            send_expo_notification(
                to=fcm_tokens,
                title=f'{car_request.get_request_type_display()} needed!',
                body=f"{car_request.get_request_type_display()} request from {car_request.customer.get_full_name()}",
                data={
                    "request_id": car_request.id,
                    "request_type": request_type_name,
                    "location": {"lat": float(latitude), "lon": float(longitude)},
                    "status": car_request.status,
                    "timestamp": car_request.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "additional_details": car_request.additional_details or "",
                }
            )


class DriverAcceptRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        driver = request.user

        # Ensure only drivers can accept requests
        if driver.user_type != 'driver':
            return Response(
                data_response(403, "Only drivers can accept requests.", {}),
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            car_request = CustomerRequest.objects.get(id=request_id, status="pending")
        except CustomerRequest.DoesNotExist:
            return Response(
                data_response(404, "Request not found or already accepted.", {}),
                status=status.HTTP_404_NOT_FOUND
            )

        # Assign driver to the request
        car_request.driver = driver
        car_request.status = "in_progress"
        car_request.save()

        # Update mapping for all drivers who received the request
        CustomerRequestDriverMapping.objects.filter(request=car_request).update(status="ignored")
        CustomerRequestDriverMapping.objects.filter(request=car_request, driver=driver).update(status="accepted")

        # Notify the customer and other drivers via WebSocket
        self.notify_customer(car_request)
        self.notify_other_drivers(car_request)

        return Response(
            data_response(200, "Request accepted successfully.", {}),
            status=status.HTTP_200_OK
        )

    def notify_customer(self, car_request):
        """
        Sends a WebSocket event to notify the customer when a driver accepts their request.
        Includes driver's real-time location and full name.
        """
        channel_layer = get_channel_layer()

        # Get driver's real-time location from Redis
        driver_location = redis_client.geopos("drivers_locations", car_request.driver.username)

        driver_lat, driver_lon = (None, None)
        if driver_location and driver_location[0]:  # Ensure location exists
            driver_lon, driver_lat = driver_location[0]  

        async_to_sync(channel_layer.group_send)(
            f"user_{car_request.customer.username}",
            {
                "type": "order_accepted_event",
                "event": "update",
                "id": car_request.id,
                "status": car_request.status,
                "otp": car_request.otp,
                "driver": {
                    "username": car_request.driver.username,
                    "name": car_request.driver.get_full_name(),
                    "phone": str(car_request.driver.phone_number),
                    "car_type": car_request.driver.get_type_display(),  # Get car type name
                    "profile_pic": car_request.driver.driver_pic.url if car_request.driver.driver_pic else None,
                },
                "location": {
                    "lat": float(driver_lat) if driver_lat else None,
                    "lon": float(driver_lon) if driver_lon else None,
                },
                "request_details": {
                    "request_type": car_request.get_request_type_display(),
                    "timestamp": car_request.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "additional_details": car_request.additional_details or "",
                },
                "customer": {
                    "username": car_request.customer.username,
                    "name": car_request.customer.get_full_name(),
                    "phone": str(car_request.customer.phone_number)
                }
            },
        )

        send_expo_notification(
            to=car_request.customer.device_id,
            title=f'Request Accepted',
            body=f"{car_request.get_request_type_display()} request accepted by {car_request.driver.get_full_name()}",
        )
        


    def notify_other_drivers(self, car_request):
        """
        Sends a WebSocket event to notify all other drivers that the request has been accepted.
        """
        channel_layer = get_channel_layer()

        # Get all drivers who received this request except the accepted driver
        other_drivers = CustomerRequestDriverMapping.objects.filter(request=car_request).exclude(driver=car_request.driver)

        for mapping in other_drivers:
            async_to_sync(channel_layer.group_send)(
                f"user_{mapping.driver.username}",
                {
                    "type": "update_booking_event",
                    "event": "update",
                    "id": car_request.id,
                    "status": "ignored",
                },
            )

class CompleteCarRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        customer = request.user

        if customer.user_type != 'customer':
            return Response(
                data_response(403, "Only Customers can complete requests.", {}),
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            car_request = CustomerRequest.objects.get(id=request_id, customer=customer, status="in_progress")
        except CustomerRequest.DoesNotExist:
            return Response(
                data_response(404, "Request not found or not assigned to you.", {}),
                status=status.HTTP_404_NOT_FOUND
            )

        # provided_otp = request.data.get("otp")

        # if str(provided_otp) != car_request.otp:
        #     return Response(
        #         data_response(400, "Invalid OTP provided.", {}),
        #         status=status.HTTP_400_BAD_REQUEST
        #     )

        car_request.status = "completed"
        car_request.save()

        redis_client.delete(f"{car_request.driver.username}_has_customer")
        redis_client.delete(f"{car_request.customer.username}_has_driver")

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{car_request.customer.username}",
            {
                "type": "order_completed_event",
                "event": "completed",
                "id": car_request.id,
                "status": "completed"
            }
        )

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{car_request.driver.username}",
            {
                "type": "order_completed_event",
                "event": "completed",
                "id": car_request.id,
                "status": "completed"
            }
        )

        return Response(
            data_response(200, "Request completed successfully.", {}),
            status=status.HTTP_200_OK
        )


class CarRequestListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        status_filter = request.query_params.get("status")
        req_data = {}
        
        if request.user.user_type == "driver":
            car_requests = CustomerRequest.objects.filter(driver=request.user).prefetch_related("driver")
        else:
            car_requests = CustomerRequest.objects.filter(customer=request.user).prefetch_related("driver")
        
        car_requests = car_requests.order_by("-timestamp")
        
        user_state = car_requests[0].status if car_requests else None
        
        if status_filter:
            car_requests = car_requests.filter(status=status_filter)
        
        response_data = []
        for request_data in car_requests:
            # if request.user.user_type == "driver":
            #     request_data.pop("otp", None)  
            response_data.append(request_data)
        
        response_requests = {}
        
        if response_data:
            req = response_data[0]
            driver_data ={}
            if req.driver:
                driver_location = redis_client.geopos("drivers_locations", req.driver.username)

                driver_lat, driver_lon = (None, None)
                if driver_location and driver_location[0]:  # Ensure location exists
                    driver_lon, driver_lat = driver_location[0]  
                driver_data = {
                        "username": req.driver.username,
                        "name": req.driver.get_full_name(),
                        "phone": str(req.driver.phone_number),
                        "car_type": req.driver.get_type_display(),
                        "profile_pic": req.driver.driver_pic.url if req.driver.driver_pic else None,
                        "location": {
                            "lat": float(driver_lat) if driver_lat else None,
                            "lon": float(driver_lon) if driver_lon else None,
                        }
                    }
            
            req_data = {
                "id": req.id,
                "request_type": req.request_type,
                "status": req.status,
                "latitude": req.latitude,
                "longitude": req.longitude,
                "timestamp": req.timestamp,
                "additional_details": req.additional_details,
                "driver": driver_data,
                "customer": {
                    "username": req.customer.username,
                    "name": req.customer.get_full_name(),
                    "phone": str(req.customer.phone_number)
                }
            }
            
        
        return Response(data_response(200, "Car requests retrieved successfully.", {"user_state":user_state,"requests": req_data}), status=status.HTTP_200_OK)
    

class CancelCarRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        user = request.user

        try:
            car_request = CustomerRequest.objects.get(id=request_id, customer=user)
        except CustomerRequest.DoesNotExist:
            return Response(
                data_response(404, "Request not found or not authorized to cancel.", {}),
                status=status.HTTP_404_NOT_FOUND
            )

        if car_request.status not in ["pending", "in_progress"]:
            return Response(
                data_response(400, "Only pending or in-progress requests can be canceled.", {}),
                status=status.HTTP_400_BAD_REQUEST
            )

        car_request.status = "canceled"
        car_request.save()

        # Delete request-driver mappings
        CustomerRequestDriverMapping.objects.filter(request=car_request)

        # Notify assigned driver if exists
        if car_request.driver:
            self.notify_driver(car_request)

        self.notify_other_drivers(car_request)

        # Notify customer
        self.notify_customer(car_request)

        return Response(
            data_response(200, "Request canceled successfully.", {}),
            status=status.HTTP_200_OK
        )

    def notify_driver(self, car_request):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{car_request.driver.username}",
            {
                "type": "update_booking_event",
                "event": "canceled",
                "id": car_request.id,
                "status": "canceled",
            },
        )

    def notify_customer(self, car_request):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{car_request.customer.username}",
            {
                "type": "order_canceled_event",
                "event": "canceled",
                "id": car_request.id,
                "status": "canceled",
            },
        )
    
    def notify_other_drivers(self, car_request):
        """
        Sends a WebSocket event to notify all other drivers that the request has been accepted.
        """
        channel_layer = get_channel_layer()

        # Get all drivers who received this request except the accepted driver
        other_drivers = CustomerRequestDriverMapping.objects.filter(request=car_request).exclude(driver=car_request.driver)

        for mapping in other_drivers:
            async_to_sync(channel_layer.group_send)(
                f"user_{mapping.driver.username}",
                {
                    "type": "update_booking_event",
                    "event": "update",
                    "id": car_request.id,
                    "status": "ignored",
                },
            )


class PendingRequestsForDriverView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        size = request.query_params.get("size")
        if size:
            try:
                size = int(size)
            except ValueError:
                size = 10
        
        size = 10

        driver = request.user

        if driver.user_type != 'driver':
            return Response(
                data_response(403, "Only drivers can access this.", {}), 
                status=403
            )

        # Get all pending requests mapped to this driver
        pending_mappings = CustomerRequestDriverMapping.objects.filter(
            driver=driver,
            status='pending',
            request__status='pending'
        ).select_related('request')

        pending_requests = [mapping.request for mapping in pending_mappings]
        serializer = CustomerRequestSerializer(pending_requests[:size], many=True)

        return Response(
            data_response(200, "Pending requests for driver fetched successfully.", serializer.data),
            status=200
        )