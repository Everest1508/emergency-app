from .views import CustomerCarRequestView,DriverAcceptRequestView, CarRequestListView, CompleteCarRequestView
from django.urls import path

urlpatterns = [
    path('request-car/', CustomerCarRequestView.as_view(), name='request-car'),
    path("accept-request/<request_id>/",DriverAcceptRequestView.as_view(), name='accept-request'),
    path("car-requests/", CarRequestListView.as_view(), name="car_requests_list"),
    path("car-requests/<int:request_id>/complete/", CompleteCarRequestView.as_view(), name="complete_car_request"),
]


