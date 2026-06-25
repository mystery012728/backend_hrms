from django.urls import path
from .views import (
    apply_leave,
    leave_list,
    leave_detail,
    accept_leave,
    reject_leave,
    leave_type_list,
    leave_balance_list,
)

urlpatterns = [
    path('', leave_list),
    path('apply-leave/', apply_leave),
    path('types/', leave_type_list),
    path('balances/', leave_balance_list),
    path('<int:pk>/', leave_detail),
    path('<int:pk>/accept/', accept_leave),
    path('<int:pk>/reject/', reject_leave),
]
