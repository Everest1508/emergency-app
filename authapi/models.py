from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.utils.crypto import get_random_string

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('driver', 'Driver'),
        ('customer', 'Customer'),
    )
    user_type = models.CharField(
        max_length=10, choices=USER_TYPE_CHOICES, default='customer'
    )
    phone_number = PhoneNumberField(null=True, unique=True)
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    forget_token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    license = models.CharField(max_length=100, null=True, blank=True)  # Driver license
    ambulance_pic = models.ImageField(upload_to='ambulances/', null=True, blank=True)  # Ambulance picture
    driver_pic = models.ImageField(upload_to='drivers/', null=True, blank=True)  # Driver picture

    def generate_verification_token(self):
        self.verification_token = get_random_string(64)
        self.save()

        
class EmailGroupModel(models.Model):
    fe_url = models.URLField(max_length=200)
    subject = models.CharField(max_length=200)
    from_email = models.CharField(max_length=50)
    body_template = models.TextField()
    type = models.CharField(max_length=50)
    
    def __str__(self) -> str:
        return self.type