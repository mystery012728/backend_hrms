from django.urls import path

from .views import (
    attendance_list,
    check_in,
    check_out,
    todays_attendance,
)

urlpatterns = [
    path('', attendance_list),
    path('check-in/', check_in),
    path('check-out/', check_out),
    path('todays-attendance/', todays_attendance),
]