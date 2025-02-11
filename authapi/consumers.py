import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import User
from rest_framework.authtoken.models import Token
from .utils import get_key_from_cookies
import urllib.parse
from django.conf import settings
import redis

redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


class UserLocationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Handles WebSocket connection.
        - Authenticates the user.
        - Validates the driver ID.
        - Adds the driver to a room group for real-time updates.
        """
        token = self.get_token_from_query_params()
        url_user_id = self.scope['url_route']['kwargs']['user_id']
        
        if not token:
            await self.close(code=4001)
            return
        
        self.user = await self.authenticate_user(url_user_id,token)
        if not self.user:
            await self.close(code=4002)
            return

        self.room_user = f'user_{self.user.username}'
        await self.channel_layer.group_add(self.room_user, self.channel_name)

        if self.user.user_type == 'driver' and self.user.type:
            self.room_drivers = f'drivers_{self.user.type}'
            await self.channel_layer.group_add(self.room_drivers, self.channel_name)

        if self.user.user_type == 'customer':
            self.room_customers = 'customers'
            await self.channel_layer.group_add(self.room_customers, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        """
        Handles WebSocket disconnection.
        - Removes the driver from the room group.
        - Marks the driver as offline in the database.
        """
        if hasattr(self, 'room_user'):
            await self.channel_layer.group_discard(self.room_user, self.channel_name)

        if hasattr(self, 'room_drivers'):
            await self.channel_layer.group_discard(self.room_drivers, self.channel_name)

        if hasattr(self, 'room_customers'):
            await self.channel_layer.group_discard(self.room_customers, self.channel_name)

        if self.user.user_type == 'driver':
            await self.mark_user_offline(self.user.username)
        
        self.remove_driver_from_redis(self.user.username, self.user.user_type)

        print(f'Driver disconnected. Close code: {close_code}')

    async def receive(self, text_data):
        """
        Handles incoming WebSocket messages.
        - Updates the driver's location in the database.
        - Broadcasts the new location to the room group.
        """
        try:
            data = json.loads(text_data)
            latitude = data.get('latitude')
            longitude = data.get('longitude')

            if latitude is None or longitude is None:
                raise ValueError("Latitude and longitude are required.")

            # Step 1: Update the driver's location in the database
            await self.update_user_location(self.user.username, latitude, longitude, self.user.user_type)

            # Step 2: Broadcast the new location to the room group
            await self.channel_layer.group_send(
                self.room_user,
                {
                    'type': 'location_update',
                    'latitude': latitude,
                    'longitude': longitude,
                }
            )
        except Exception as e:
            print(f'Error processing message: {e}')
            await self.send(text_data=json.dumps({'error': str(e)}))

    async def location_update(self, event):
        """
        Sends location updates to the WebSocket client.
        """
        await self.send(text_data=json.dumps({
            'latitude': event['latitude'],
            'longitude': event['longitude'],
        }))
    
    async def new_booking_event(self, event):
        """
        Handles new car request events and sends them to drivers.
        """
        await self.send(text_data=json.dumps(event))
        
    async def order_accepted_event(self, event):
        """
        Handles user update event when driver accepts request.
        """
        await self.send(text_data=json.dumps(event))
        
    @database_sync_to_async
    def authenticate_user(self, user_id,token):
        try:
            tkn = Token.objects.get(key=token)
            return tkn.user if user_id == tkn.user.username else None
        except Token.DoesNotExist:
            return None

    @database_sync_to_async
    def update_user_location(self, username, latitude, longitude, type):
        if type == "customer":
            redis_client.geoadd("customers_locations", (longitude, latitude, username))
        elif type == "driver":
            redis_client.geoadd("drivers_locations", (longitude, latitude, username))

    @database_sync_to_async
    def mark_user_offline(self, driver_id):
        """
        Marks the driver as offline in the database.
        """
        # driver = Driver.objects.get(id=driver_id)
        # driver.is_available = False
        # driver.save()
        print("disconnected")
        
    def get_token_from_query_params(self):
        """
        Extracts the token from WebSocket query parameters.
        """
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        query_params = urllib.parse.parse_qs(query_string)
        return query_params.get('token', [None])[0]

    def remove_driver_from_redis(self, username, type):
        """
        Removes a driver from Redis when they disconnect.
        """
        if type == "customer":
            redis_client.zrem("customers_locations", username)
        elif type == "driver":
            redis_client.zrem("drivers_locations", username)
