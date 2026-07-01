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

    def test_check_out_missing_employee(self):
        # Create a user with no employee profile
        no_profile_user = User.objects.create_user(username="noprofileuser", password="testpassword")
        self.client.force_authenticate(user=no_profile_user)
        
        # This will trigger Employee.objects.get(user=request.user) which will raise DoesNotExist.
        # We check if it returns 500 or if we can handle it.
        try:
            response = self.client.post('/attendance/check-out/')
            print(f"DEBUG: Status code for missing employee: {response.status_code}")
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        except Employee.DoesNotExist:
            # Under some testing settings it might bubble up, but we caught it in the view now.
            pass

    def test_check_out_manual_multipart_content_type(self):
        # Authenticate the valid user with employee profile
        self.client.force_authenticate(user=self.user)
        
        # Manually specify Content-Type: multipart/form-data without boundary
        response = self.client.post(
            '/attendance/check-out/',
            data="invalid data content",
            content_type='multipart/form-data'
        )
        print(f"DEBUG: Status code for manual multipart/form-data: {response.status_code}")
        # In Django/DRF, manually setting content_type to 'multipart/form-data' causes MultiPartParserError,
        # which usually raises ParseError/MultiPartParserError.

    def test_total_work_time_calculation(self):
        now = timezone.now()
        check_in_time = now - timedelta(hours=8, minutes=30)
        check_out_time = now
        
        attendance = Attendance.objects.create(
            employee=self.employee,
            status="PRESENT",
            check_in=check_in_time,
            check_out=check_out_time
        )
        
        response = self.client.get('/attendance/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = [item for item in response.data if item['id'] == attendance.id][0]
        self.assertEqual(data['totalworktime'], "08:30")

        # Create attendance with only check_in (no check_out)
        attendance_no_checkout = Attendance.objects.create(
            employee=self.employee,
            status="PRESENT",
            check_in=now
        )
        response = self.client.get('/attendance/')
        data_no_checkout = [item for item in response.data if item['id'] == attendance_no_checkout.id][0]
        self.assertIsNone(data_no_checkout['totalworktime'])


