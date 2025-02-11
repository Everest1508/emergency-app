from .views import CustomerCarRequestView,DriverAcceptRequestView
from django.urls import path

urlpatterns = [
    path('request-car/', CustomerCarRequestView.as_view(), name='request-car'),
    path("accept-request/<request_id>/",DriverAcceptRequestView.as_view(), name='accept-request')
]


