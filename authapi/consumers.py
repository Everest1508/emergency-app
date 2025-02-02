import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import User
from rest_framework.authtoken.models import Token
from .utils import get_key_from_cookies

class UserLocationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Handles WebSocket connection.
        - Authenticates the user.
        - Validates the driver ID.
        - Adds the driver to a room group for real-time updates.
        """
        token = get_key_from_cookies(scope=self.scope,key="token")
        url_user_id = self.scope['url_route']['kwargs']['user_id']
        
        if not token:
            await self.close(code=4001)
            return
        
        self.user = await self.authenticate_user(url_user_id,token)
        print(self.user,"*"*100)
        if not self.user:
            await self.close(code=4002)
            return

        self.room_group_name = f'user_{self.user.username}'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        """
        Handles WebSocket disconnection.
        - Removes the driver from the room group.
        - Marks the driver as offline in the database.
        """
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

            # Step 2: Mark the driver as offline in the database
            await self.mark_user_offline(self.user.username)

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
            await self.update_user_location(self.user.username, latitude, longitude)

            # Step 2: Broadcast the new location to the room group
            await self.channel_layer.group_send(
                self.room_group_name,
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

    @database_sync_to_async
    def authenticate_user(self, user_id,token):
        try:
            tkn = Token.objects.get(key=token)
            return tkn.user if user_id == tkn.user.username else None
        except Token.DoesNotExist:
            return None

    @database_sync_to_async
    def update_user_location(self, driver_id, latitude, longitude):
        """
        Updates the driver's location in the database.
        """
        # driver = Driver.objects.get(id=driver_id)
        # driver.latitude = latitude
        # driver.longitude = longitude
        # driver.save()
        print(driver_id,longitude,latitude)

    @database_sync_to_async
    def mark_user_offline(self, driver_id):
        """
        Marks the driver as offline in the database.
        """
        # driver = Driver.objects.get(id=driver_id)
        # driver.is_available = False
        # driver.save()
        print("disconnected")