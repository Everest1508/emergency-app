from django.contrib import admin
from .models import CustomerRequest, CustomerRequestDriverMapping
# Register your models here.

admin.site.register(CustomerRequest)
admin.site.register(CustomerRequestDriverMapping)