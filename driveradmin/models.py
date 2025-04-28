from django.db import models
from django.conf import settings
from channels.db import database_sync_to_async

class UserStatusHistory(models.Model):
    STATUS_CHOICES = (
        ('online', 'Online'),
        ('offline', 'Offline'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    user_status = models.CharField(max_length=250, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.status} at {self.timestamp}"


class UserOnDutyHistory(models.Model):
    STATUS_CHOICES = (
        ("on", "ON DUTY"),
        ("off", "OFF DUTY"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(choices=STATUS_CHOICES, max_length=250)
    timestamp = models.DateTimeField(auto_now_add=True)

@database_sync_to_async
def create_status_history(user, status, user_status):
    """
    Helper function to create a user status history entry.
    """
    return UserStatusHistory.objects.create(user=user, status=status, user_status= user_status)
