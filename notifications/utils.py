from django.contrib.auth.models import User
from employees.models import Employee
from .models import Notification

def create_notification(user, title, message, image=None):
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message
    )
    if image:
        notification.image = image
        notification.save()
    return notification

def notify_hr_admins(company, title, message, image=None):
    if not company:
        return
    recipients = Employee.objects.filter(
        company=company,
        role__in=['HR', 'ADMIN', 'SUPER_ADMIN']
    ).select_related('user')
    
    for emp in recipients:
        if emp.user:
            create_notification(emp.user, title, message, image)
