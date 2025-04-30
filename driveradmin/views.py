# views.py
import json
from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
import redis
from django.db.models import OuterRef, Subquery
from .models import UserStatusHistory, UserOnDutyHistory 
from authapi.models import User
from django.conf import settings
from rest_framework.authtoken.models import Token

pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)
redis_client = redis.Redis(connection_pool=pool)


def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            Token.objects.get_or_create(user=user)
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'login/index.html', {'error': 'Invalid username or password'})

    return render(request, 'login/index.html')



@login_required(login_url='zora_login')
def dashboard_view(request):
    admin = request.user
    drivers_queryset = User.objects.filter(user_type="driver", added_by=admin)

    # Get latest status and duty status per driver using subqueries
    latest_statuses = UserStatusHistory.objects.filter(user=OuterRef('pk')).order_by('-timestamp')
    latest_duties = UserOnDutyHistory.objects.filter(user=OuterRef('pk')).order_by('-timestamp')

    drivers = []

    for driver in drivers_queryset.annotate(
        latest_status=Subquery(latest_statuses.values('status')[:1]),
        latest_user_status=Subquery(latest_statuses.values('user_status')[:1]),
        latest_duty=Subquery(latest_duties.values('status')[:1])
    ):
        # Get location from Redis
        location = redis_client.geopos("drivers_locations", driver.username)

        if location and location[0]:
            lng, lat = location[0]

            drivers.append({
                "id": driver.id,
                "name": driver.username,
                "lat": lat,
                "lng": lng,
                "status": driver.latest_status or "Unknown",
                "dutyStatus": "On Duty" if driver.latest_duty == "on" else "Off Duty"
            })
    drivers_json = json.dumps(drivers)
    print(drivers_json)
    return render(request, 'dashboard/index.html', {"drivers_json": drivers_json})


@login_required(login_url='zora_login')
def driver_view(request):
    admin = request.user
    drivers_queryset = User.objects.filter(user_type="driver", added_by=admin)

    # Get latest status and duty status per driver using subqueries
    latest_statuses = UserStatusHistory.objects.filter(user=OuterRef('pk')).order_by('-timestamp')
    latest_duties = UserOnDutyHistory.objects.filter(user=OuterRef('pk')).order_by('-timestamp')

    drivers = []

    for driver in drivers_queryset.annotate(
        latest_status=Subquery(latest_statuses.values('status')[:1]),
        latest_user_status=Subquery(latest_statuses.values('user_status')[:1]),
        latest_duty=Subquery(latest_duties.values('status')[:1])
    ):
        # Get location from Redis
        location = redis_client.geopos("drivers_locations", driver.username)

        if location and location[0]:
            lng, lat = location[0]

            drivers.append({
                "id": driver.id,
                "name": driver.username,
                "lat": lat,
                "lng": lng,
                "status": driver.latest_status or "Unknown",
                "dutyStatus": "On Duty" if driver.latest_duty == "on" else "Off Duty"
            })

    print(drivers_json)

    drivers_json = json.dumps(drivers)
    return render(request, 'home/index.html', {"drivers_json": drivers_json})
