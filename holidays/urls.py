from django.urls import path
from .views import holiday_list, holiday_detail

urlpatterns = [
    path('', holiday_list),
    path('<int:pk>/', holiday_detail),
]
