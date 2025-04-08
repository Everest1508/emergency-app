from .views import (
    CustomerCarRequestView,DriverAcceptRequestView, CarRequestListView, 
    CompleteCarRequestView, CancelCarRequestView, PendingRequestsForDriverView
)
from django.urls import path

urlpatterns = [
    path('request-car/', CustomerCarRequestView.as_view(), name='request-car'),
    path("accept-request/<request_id>/",DriverAcceptRequestView.as_view(), name='accept-request'),
    path("car-requests/", CarRequestListView.as_view(), name="car_requests_list"),
    path("car-requests/<int:request_id>/complete/", CompleteCarRequestView.as_view(), name="complete_car_request"),
    path("car-requests/<int:request_id>/cancel/", CancelCarRequestView.as_view(), name="cancel_car_request"),
    path('car-requests/pending-requests/', PendingRequestsForDriverView.as_view(), name='driver-pending-requests'),
]


