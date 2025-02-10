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
