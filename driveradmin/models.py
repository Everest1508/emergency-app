from django.db import models
from django.conf import settings

class UserStatusHistory(models.Model):
    STATUS_CHOICES = (
        ('online', 'Online'),
        ('offline', 'Offline'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.status} at {self.timestamp}"


def create_status_history(user, status):
    """
    Helper function to create a user status history entry.
    """
    return UserStatusHistory.objects.create(user=user, status=status)
