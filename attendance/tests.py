from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, timedelta

from employees.models import Employee
from attendance.models import Attendance

class AttendanceAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.employee = Employee.objects.create(
            user=self.user,
            name="Test Employee",
            email="test@example.com",
            phone="1234567890",
            designation="Developer",
            department="IT",
            joining_date=date.today()
        )
        self.client.force_authenticate(user=self.user)

    def test_attendance_list_filtering(self):
        # Create attendance for 3 different days
        today = date.today()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)

        # We cannot use auto_now_add=True directly to set custom dates on creation easily
        # because auto_now_add overrides the input on create, but we can update it afterwards
        att1 = Attendance.objects.create(employee=self.employee, status="PRESENT")
        Attendance.objects.filter(id=att1.id).update(date=today)

        att2 = Attendance.objects.create(employee=self.employee, status="PRESENT")
        Attendance.objects.filter(id=att2.id).update(date=yesterday)

        att3 = Attendance.objects.create(employee=self.employee, status="PRESENT")
        Attendance.objects.filter(id=att3.id).update(date=two_days_ago)

        # Get all attendance
        response = self.client.get('/attendance/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

        # Filter by start_date
        response = self.client.get(f'/attendance/?start_date={yesterday}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # today and yesterday

        # Filter by end_date
        response = self.client.get(f'/attendance/?end_date={yesterday}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # yesterday and two_days_ago

        # Filter by both
        response = self.client.get(f'/attendance/?start_date={yesterday}&end_date={yesterday}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['date'], str(yesterday))

    def test_todays_attendance(self):
        # Initially, no attendance marked for today
        response = self.client.get('/attendance/todays-attendance/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Create attendance for today
        Attendance.objects.create(employee=self.employee, status="PRESENT")

        # Fetch today's attendance
        response = self.client.get('/attendance/todays-attendance/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'PRESENT')
        self.assertEqual(response.data['date'], str(date.today()))
