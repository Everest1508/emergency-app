from django.db import models

class WebsiteSettings(models.Model):
    site_name = models.CharField(max_length=255)
    site_description = models.TextField()
    contact_email = models.EmailField()
    maintenance_mode = models.BooleanField(default=False)

    def __str__(self):
        return self.site_name
    
class ApplicationSettings(models.Model):
    maximum_requests_per_user = models.IntegerField(default=1)
    search_radius = models.IntegerField(default=10)
    send_request_to = models.CharField(max_length=50, choices=(('all', 'All Drivers'), ('type', 'Only to requested Type')), default='all')

    def __str__(self):
        return f"Application Settings: maximum_requests_per_user={self.maximum_requests_per_user}, search_radius={self.search_radius}, send_request_to={self.send_request_to}"