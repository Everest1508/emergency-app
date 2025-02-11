from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from orders.models import CustomerRequest
from .serializers import CustomerRequestSerializer
from utils.response import data_response
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import redis
from django.conf import settings
from authapi.models import User

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

        data = request.data.copy()
        data["customer"] = user.id
        
        serializer = CustomerRequestSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            self.send_request_to_nearby_drivers(serializer.instance)
            return Response(
                data_response(201, "Car request created successfully", serializer.data),
                status=status.HTTP_201_CREATED
            )
        
        # Handling errors
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
    
    def send_request_to_nearby_drivers(self, car_request):
        """
        Finds nearby drivers and sends WebSocket event.
        """
        latitude = car_request.latitude
        longitude = car_request.longitude
        request_type = car_request.request_type
        radius_km = 10  

        nearby_drivers = redis_client.georadius(
            "drivers_locations", float(longitude), float(latitude),
            radius_km, unit="km", withcoord=False
        )

        request_type_dict = dict(CustomerRequest.REQUEST_TYPES)
        request_type_name = request_type_dict.get(request_type, "Unknown")

        channel_layer = get_channel_layer()
        for driver_username in nearby_drivers:
            async_to_sync(channel_layer.group_send)(
                f"user_{driver_username}",
                {
                    "type": "new_booking_event",
                    "event": "new",
                    "id": car_request.id,
                    "booking_type": "booking",
                    "data": {
                        "user": {
                            "name": car_request.customer.username,
                            "phone": str(car_request.customer.phone_number),
                        },
                        "request_type": request_type_name, 
                        "location": {"lat": float(latitude), "lon": float(longitude)},
                        "status": car_request.status,
                        "timestamp": car_request.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "additional_details": car_request.additional_details or "",
                    },
                },
            )

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from orders.models import CustomerRequest
from utils.response import data_response
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

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

        # Notify the customer via WebSocket
        self.notify_customer(car_request)

        return Response(
            data_response(200, "Request accepted successfully.", {}),
            status=status.HTTP_200_OK
        )

    def notify_customer(self, car_request):
        """
        Sends a WebSocket event to notify the customer when a driver accepts their request.
        """
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{car_request.customer.username}",
            {
                "type": "order_accepted_event",
                "event": "update",
                "id": car_request.id,
                "status": car_request.status,
                "driver": {
                    "name": car_request.driver.username,
                    "phone": str(car_request.driver.phone_number),
                },
                "location": {
                    "lat": float(car_request.latitude),
                    "lon": float(car_request.longitude),
                },
            },
        )
