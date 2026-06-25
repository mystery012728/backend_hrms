from django.db import models
from employees.models import Employee
from companies.models import Company


class LeaveType(models.Model):

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='leave_types',
        null=True,
        blank=True
    )

    name = models.CharField(max_length=100)
    default_annual_quota = models.IntegerField(default=12)

    def __str__(self):
        return self.name


class LeaveBalance(models.Model):

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='leave_balances'
    )

    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name='balances'
    )

    year = models.IntegerField()
    allocated_days = models.IntegerField()
    used_days = models.IntegerField(default=0)

    class Meta:
        unique_together = ('employee', 'leave_type', 'year')

    @property
    def remaining_days(self):
        return self.allocated_days - self.used_days

    def __str__(self):
        return f"{self.employee.name} - {self.leave_type.name} ({self.year}): {self.remaining_days}/{self.allocated_days} remaining"


class Leave(models.Model):

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='leaves'
    )

    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name='leaves',
        null=True,
        blank=True
    )

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    total_days = models.IntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.employee.name} - {self.status} ({self.total_days} days)"


class LeaveDate(models.Model):

    leave = models.ForeignKey(
        Leave,
        on_delete=models.CASCADE,
        related_name='dates'
    )

    date = models.DateField()

    def __str__(self):
        return f"{self.leave.employee.name} - {self.date}"
