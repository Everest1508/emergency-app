# serializers.py
from rest_framework import serializers
from .models import CustomerRequest

class CustomerRequestSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    class Meta:
        model = CustomerRequest
        fields = ['id','user', 'customer', 'request_type', 'latitude', 'longitude', 'additional_details']
    
    def get_user(self, obj):
        return {
            "name": obj.customer.username, 
            "phone": str(obj.customer.phone_number)
        }
