# serializers.py
from rest_framework import serializers
from .models import CustomerRequest

class CustomerRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerRequest
        fields = ['customer', 'request_type', 'latitude', 'longitude', 'additional_details']
