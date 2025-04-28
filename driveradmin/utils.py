from django.utils import timezone
from datetime import timedelta
from .models import UserStatusHistory, UserOnDutyHistory


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


def get_today_on_duty_time(user):
    """
    Fetches today's on-duty time for the user. This will match the first "on duty"
    entry and the last "off duty" entry to calculate the total time spent on duty today.
    """
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)

    # Fetch the first "on duty" entry for today
    on_duty_entry = UserOnDutyHistory.objects.filter(
        user=user,
        status='on',
        timestamp__range=[today_start, today_end]
    ).order_by('timestamp').first()

    # Fetch the last "off duty" entry for today
    off_duty_entry = UserOnDutyHistory.objects.filter(
        user=user,
        status='off',
        timestamp__range=[today_start, today_end]
    ).order_by('timestamp').last()

    if on_duty_entry and off_duty_entry:
        # Calculate the on-duty time
        start_time = on_duty_entry.timestamp
        end_time = off_duty_entry.timestamp
        on_duty_duration = end_time - start_time
        return on_duty_duration
    elif on_duty_entry:
        # If user is still on duty, return the time from "on duty" until now
        start_time = on_duty_entry.timestamp
        end_time = timezone.now()
        on_duty_duration = end_time - start_time
        return on_duty_duration
    else:
        # No "on duty" entries for today
        return timedelta(0)
