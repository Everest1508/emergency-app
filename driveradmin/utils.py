from django.utils import timezone
from datetime import timedelta
from .models import UserStatusHistory

def calculate_offline_time(user):
    """
    Calculates the total offline time for a user by checking
    the difference between the "online" and "offline" status records.
    """
    offline_entries = UserStatusHistory.objects.filter(user=user, status='offline')
    total_offline_time = timedelta()

    for offline_entry in offline_entries:
        online_entry = UserStatusHistory.objects.filter(
            user=user,
            status='online',
            timestamp__lt=offline_entry.timestamp
        ).last()
        
        if online_entry:
            offline_duration = offline_entry.timestamp - online_entry.timestamp
            total_offline_time += offline_duration

    return total_offline_time

