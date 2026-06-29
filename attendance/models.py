from django.db import models
from employees.models import Employee


class Attendance(models.Model):

    STATUS_CHOICES = (
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('HALF_DAY', 'Half Day'),
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE
    )

    date = models.DateField(
        auto_now_add=True
    )

    check_in = models.DateTimeField(
        null=True,
        blank=True
    )

    check_out = models.DateTimeField(
        null=True,
        blank=True
    )

    selfie = models.ImageField(
        upload_to='attendance/'
    )

    checkout_selfie = models.ImageField(
        upload_to='attendance_checkout/',
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PRESENT'
    )

    def __str__(self):
        return f"{self.employee.name} - {self.date}"