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

    def save(self, *args, **kwargs):
        # Sync email to the associated User if it exists
        if self.user and self.user.email != self.email:
            self.user.email = self.email
            self.user.save(update_fields=['email'])
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name