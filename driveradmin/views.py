# views.py
from django.utils import timezone
from datetime import timedelta
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
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

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
                "username": driver.username,
                "lat": lat,
                "lng": lng,
                "status": driver.latest_status or "Unknown",
                "dutyStatus": "On Duty" if driver.latest_duty == "on" else "Off Duty"
            })
    drivers_json = json.dumps(drivers)
    print(drivers_json)
    tkn,_ =  Token.objects.get_or_create(user=request.user)
    return render(request, 'dashboard/index.html', {"drivers_json": drivers_json,"token":tkn})


@login_required(login_url='zora_login')
def driver_view(request):
    drivers = User.objects.filter(user_type='driver', added_by=request.user)

    total_drivers = drivers.count()
    online_drivers = drivers.filter(device_id__isnull=False).count()
    on_duty_drivers = drivers.filter(on_duty=True).count()

    recent_threshold = timezone.now() - timedelta(days=1)
    recent_drivers = drivers.filter(date_joined__gte=recent_threshold).count()

    driver_list = []
    for d in drivers:
        status = "offline"
        if d.on_duty:
            status = "onDuty"
        elif d.device_id:
            status = "online"

        driver_list.append({
            "name": d.get_full_name() or d.username,
            "status": status,
            "onlineTime": d.date_joined.strftime('%I:%M %p'),
            "offlineTime": "-",  # Placeholder for future logic
        })

    context = {
        "total_drivers": total_drivers,
        "online_drivers": online_drivers,
        "on_duty_drivers": on_duty_drivers,
        "recent_drivers": recent_drivers,
        "driver_data": driver_list,
    }
    return render(request, 'home/index.html', context)



@csrf_exempt
@login_required(login_url='zora_login')
def get_location_history(request, username):
    """
    API to fetch the location history of a user from Redis.
    Always returns 200 OK with empty data if no history is found.
    """
    try:
        # Fetch the location history list for the user from Redis
        location_history = redis_client.lrange(f"driver_location_history:{username}", 0, -1)

        # Convert to Python dicts (if data exists)
        if location_history:
            location_history = [json.loads(item) for item in location_history]
        else:
            location_history = []

        # Prepare the response data
        response_data = {
            "username": username,
            "location_history": location_history
        }

        return JsonResponse(response_data, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)