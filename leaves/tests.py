from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date

from employees.models import Employee
from companies.models import Company
from .models import Leave, LeaveDate, LeaveType, LeaveBalance


class LeaveEntitlementAPITests(APITestCase):

    def setUp(self):
        # Create company
        self.company = Company.objects.create(name="HR Corp", email="hr@example.com", address="HQ")

        # Create leave types
        self.casual_leave = LeaveType.objects.create(
            company=self.company,
            name="Casual Leave",
            default_annual_quota=12
        )
        self.sick_leave = LeaveType.objects.create(
            company=self.company,
            name="Sick Leave",
            default_annual_quota=6
        )

        # Create Employee One (Company)
        self.employee_user = User.objects.create_user(username="emp1", password="password")
        self.employee = Employee.objects.create(
            user=self.employee_user,
            company=self.company,
            name="Employee One",
            email="emp1@example.com",
            phone="1111111111",
            role="EMPLOYEE",
            designation="Dev",
            department="IT",
            joining_date=date.today()
        )

        # Create HR User (Company)
        self.hr_user = User.objects.create_user(username="hr", password="password")
        self.hr = Employee.objects.create(
            user=self.hr_user,
            company=self.company,
            name="HR Manager",
            email="hr@example.com",
            phone="2222222222",
            role="HR",
            designation="Manager",
            department="HR",
            joining_date=date.today()
        )

    def test_apply_leave_success_and_auto_balance_init(self):
        self.client.force_authenticate(user=self.employee_user)

        data = {
            "leave_type": self.casual_leave.id,
            "dates": ["2026-07-01", "2026-07-02", "2026-07-03"],
            "reason": "Trip"
        }

        # Check balance records don't exist yet
        self.assertFalse(LeaveBalance.objects.filter(employee=self.employee, leave_type=self.casual_leave).exists())

        response = self.client.post('/leaves/apply-leave/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['total_days'], 3)
        self.assertEqual(response.data['leave_type'], self.casual_leave.id)

        # Check that LeaveBalance was auto-initialized
        balance = LeaveBalance.objects.get(employee=self.employee, leave_type=self.casual_leave)
        self.assertEqual(balance.allocated_days, 12)
        # Apply leave creates a PENDING request, so it should not deduct yet
        self.assertEqual(balance.used_days, 0)
        self.assertEqual(balance.remaining_days, 12)

    def test_apply_leave_insufficient_balance(self):
        self.client.force_authenticate(user=self.employee_user)

        # Apply for 13 days of Casual Leave (quota is 12)
        dates = [f"2026-07-{str(i).zfill(2)}" for i in range(1, 14)]
        data = {
            "leave_type": self.casual_leave.id,
            "dates": dates,
            "reason": "Long trip"
        }

        response = self.client.post('/leaves/apply-leave/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient leave balance", response.data['message'])

    def test_apply_leave_overlap_prevention(self):
        self.client.force_authenticate(user=self.employee_user)

        # Apply for first leave
        data1 = {
            "leave_type": self.casual_leave.id,
            "dates": ["2026-07-01", "2026-07-02"],
            "reason": "Personal"
        }
        response1 = self.client.post('/leaves/apply-leave/', data1, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Attempt to apply for overlapping leave
        data2 = {
            "leave_type": self.sick_leave.id,
            "dates": ["2026-07-02", "2026-07-03"],
            "reason": "Sick"
        }
        response2 = self.client.post('/leaves/apply-leave/', data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already applied for leave on 2026-07-02", response2.data['message'])

    def test_accept_leave_deducts_balance(self):
        # Create a pending leave request
        leave = Leave.objects.create(
            employee=self.employee,
            leave_type=self.casual_leave,
            reason="Trip",
            total_days=3
        )
        # Create leave dates
        LeaveDate.objects.create(leave=leave, date=date(2026, 7, 1))
        LeaveDate.objects.create(leave=leave, date=date(2026, 7, 2))
        LeaveDate.objects.create(leave=leave, date=date(2026, 7, 3))

        # Perform acceptance as HR
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.post(f'/leaves/{leave.id}/accept/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check balance
        balance = LeaveBalance.objects.get(employee=self.employee, leave_type=self.casual_leave)
        self.assertEqual(balance.used_days, 3)
        self.assertEqual(balance.remaining_days, 9)

    def test_reject_leave_refunds_balance(self):
        # Create a leave request
        leave = Leave.objects.create(
            employee=self.employee,
            leave_type=self.casual_leave,
            reason="Trip",
            total_days=3,
            status="ACCEPTED"
        )
        LeaveDate.objects.create(leave=leave, date=date(2026, 7, 1))
        LeaveDate.objects.create(leave=leave, date=date(2026, 7, 2))
        LeaveDate.objects.create(leave=leave, date=date(2026, 7, 3))

        # Manually initialize balance to show 3 days used
        balance = LeaveBalance.objects.create(
            employee=self.employee,
            leave_type=self.casual_leave,
            year=2026,
            allocated_days=12,
            used_days=3
        )

        # Perform rejection as HR -> should credit back the days
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.post(f'/leaves/{leave.id}/reject/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check balance is refunded
        balance.refresh_from_db()
        self.assertEqual(balance.used_days, 0)
        self.assertEqual(balance.remaining_days, 12)
