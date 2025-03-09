from django.db import models

class CustomerRequest(models.Model):
    REQUEST_TYPES = [
        ('0', 'Ambulance'),
        ('1', 'Fire Brigade'),
        ('2', 'Police'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    customer = models.ForeignKey("authapi.User", on_delete=models.CASCADE, related_name="customer")
    driver = models.ForeignKey("authapi.User", on_delete=models.CASCADE, related_name="driver", blank=True, null=True)
    request_type = models.CharField(max_length=50, choices=REQUEST_TYPES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
    additional_details = models.TextField(blank=True, null=True)
    otp = models.CharField(max_length=6, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.otp:
            self.otp = self.generate_otp()

        super().save(*args, **kwargs)
    
    def generate_otp(self):
        import random
        return str(random.randint(100000, 999999))
    
    def __str__(self):
        return f"Request from {self.customer} ({self.request_type}) - {self.status}"


class CustomerRequestDriverMapping(models.Model):
    request = models.ForeignKey(CustomerRequest, on_delete=models.CASCADE, related_name="driver_mappings")
    driver = models.ForeignKey("authapi.User", on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[("pending", "Pending"), ("ignored", "Ignored"), ("accepted", "Accepted")], default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('request', 'driver')
