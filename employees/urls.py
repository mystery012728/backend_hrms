from django.urls import path
from .views import employee_list, employee_detail

urlpatterns = [
    path('', employee_list),
    path('<int:pk>/', employee_detail),
]