from django.urls import path
from .views import RegisterAPIView, LoginAPIView, LogoutAPIView,verify_account,ResendVerificationEmailAPIView,DriverRegisterAPIView,ForgotPasswordAPIView,ResetPasswordAPIView

urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("verify-email/<str:token>/", verify_account, name="verify-email"),
    path("resend-verification/",ResendVerificationEmailAPIView.as_view()),
    path('driver/register/', DriverRegisterAPIView.as_view(), name='driver-register'),
    path('forgot-password/', ForgotPasswordAPIView.as_view(), name='forgot-password'),
    path('reset-password/<str:token>/', ResetPasswordAPIView.as_view(), name='reset-password'),
]
