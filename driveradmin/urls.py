# urls.py
from django.urls import path
from .views import login_view, dashboard_view, driver_view,get_location_history

urlpatterns = [
    path('auth/login/', login_view, name='zora_login'),
    path('', dashboard_view, name='dashboard'),
    path('home/', driver_view, name='driver'),
    path("get-location-history/<str:username>/", get_location_history,name='driver_location_history'),
]
