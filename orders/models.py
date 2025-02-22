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
    latitude = models.DecimalField(max_digits=9, decimal_places=10)
    longitude = models.DecimalField(max_digits=9, decimal_places=10)
    timestamp = models.DateTimeField(auto_now_add=True)
    additional_details = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Request from {self.customer_name} ({self.request_type}) - {self.status}"
