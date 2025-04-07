from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.utils.crypto import get_random_string

from utils.email import send_dynamic_email

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('driver', 'Driver'),
        ('customer', 'Customer'),
    )
    
    CAR_TYPE_CHOICES = (
        ('0', 'Ambulance'),
        ('1', 'Police'),
        ('2', 'Firebrigade'),
    )

    VERIFICATION_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('email_ready', 'Ready for Email Send'),
        ('email_sent', 'Email Sent'),
    )

    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='customer')
    phone_number = PhoneNumberField(null=True, unique=True)
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    forget_token = models.CharField(max_length=64, unique=True, blank=True, null=True)
    license_pic = models.ImageField(upload_to='license/', null=True, blank=True)
    driver_pic = models.ImageField(upload_to='drivers/', null=True, blank=True)
    type = models.CharField(choices=CAR_TYPE_CHOICES, max_length=50, null=True, blank=True)
    remark = models.TextField(null=True, blank=True)
    device_id = models.CharField(max_length=200, null=True, blank=True)
    verification_status = models.CharField(
        max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='pending'
    )

    def save(self, *args, **kwargs):
        if self.verification_status == "email_ready":
            self.send_verification_email()
            self.verification_status = "email_sent"
        elif self.remark and self.verification_status == "pending":
            self.send_remark_email()
            self.verification_status = "email_sent"
        super().save(*args, **kwargs)

    def send_verification_email(self):
        """Function to send verification email automatically"""
        try:
            email_template = EmailGroupModel.objects.get(type="driver-verified")
            context_data = {"username": self.first_name}
            email_response = send_dynamic_email(
                subject=email_template.subject,
                from_email=email_template.from_email,
                recipient_email=self.email,
                body_template=email_template.body_template,
                context_data=context_data,
            )
            if email_response["status"] != "error":
                self.is_verified = True
        except EmailGroupModel.DoesNotExist:
            pass  # Handle error if needed

    def send_remark_email(self):
        """Function to send remark email automatically"""
        try:
            email_template = EmailGroupModel.objects.get(type="driver-remark")
            context_data = {"username": self.first_name, "remark": self.remark}
            send_dynamic_email(
                subject=email_template.subject,
                from_email=email_template.from_email,
                recipient_email=self.email,
                body_template=email_template.body_template,
                context_data=context_data,
            )
        except EmailGroupModel.DoesNotExist:
            pass  # Handle error if needed


    def generate_verification_token(self):
        self.verification_token = get_random_string(64)
        self.save()
    
    def __str__(self):
        return super().__str__() + " " + self.user_type

        
class EmailGroupModel(models.Model):
    fe_url = models.URLField(max_length=200)
    subject = models.CharField(max_length=200)
    from_email = models.CharField(max_length=50)
    body_template = models.TextField()
    type = models.CharField(max_length=50)
    
    def __str__(self) -> str:
        return self.type
    
class CarPic(models.Model):
    user = models.ForeignKey("authapi.User",  on_delete=models.CASCADE)
    image = models.ImageField(upload_to='car/')