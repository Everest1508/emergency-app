from .views import CustomerCarRequestView
from django.urls import path

urlpatterns = [
    path('request-car/', CustomerCarRequestView.as_view(), name='request-car'),
]


