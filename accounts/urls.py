from django.urls import path
from .views import (
    login,
    send_otp,
    verify_otp,
    reset_password,
)

urlpatterns = [
    path('login/', login),
    path('send-otp/', send_otp),
    path('verify-otp/', verify_otp),
    path('reset-password/', reset_password),
]