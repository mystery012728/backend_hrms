from django.db import models
from companies.models import Company
from django.contrib.auth.models import User

class Employee(models.Model):

    ROLE_CHOICES = (
        ('SUPER_ADMIN', 'Super Admin'),
        ('ADMIN', 'Admin'),
        ('HR', 'HR'),
        ('EMPLOYEE', 'Employee'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='EMPLOYEE'
    )

    designation = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    joining_date = models.DateField()

    profile_image = models.ImageField(
      upload_to='employees/',
      null=True,
      blank=True
    )

    def __str__(self):
        return self.name


from django.db.models.signals import post_save
from django.dispatch import receiver
import re
import secrets
import string
from django.core.mail import send_mail
from django.conf import settings

@receiver(post_save, sender=Employee)
def create_employee_user_profile(sender, instance, created, **kwargs):
    if created and not instance.user:
        # Generate unique username based on the email
        email = instance.email
        base_username = email.split('@')[0]
        base_username = re.sub(r'[^a-zA-Z0-9_.-]', '', base_username)
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # Generate a secure random password
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for _ in range(10))

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # Update the employee record
        # Note: We use update() to avoid triggering the post_save signal recursively
        Employee.objects.filter(pk=instance.pk).update(user=user)
        instance.user = user

        # Send email with credentials
        subject = "Welcome to HRMS - Your Account Credentials"
        email_message = f"Hello {instance.name},\n\nWelcome to HRMS! Your account has been successfully created.\n\nHere are your login credentials:\nUsername: {username}\nPassword: {password}\n\nPlease login and update your password.\n\nBest regards,\nHR Team"
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@hrms.com')
        send_mail(
            subject=subject,
            message=email_message,
            from_email=from_email,
            recipient_list=[email],
            fail_silently=False
        )