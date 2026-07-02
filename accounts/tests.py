from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date

from employees.models import Employee
from .models import OTPVerification


class ForgotPasswordAPITests(APITestCase):

    def setUp(self):
        # Create standard user
        self.user = User.objects.create_user(username="testuser", password="old_password", email="test@hrms.com")
        self.employee = Employee.objects.create(
            user=self.user,
            name="Test User",
            email="test@hrms.com",
            phone="1234567890",
            role="EMPLOYEE",
            designation="Developer",
            department="IT",
            joining_date=date.today()
        )

    def test_send_otp_success(self):
        data = {
            "email": "test@hrms.com"
        }
        response = self.client.post('/accounts/send-otp/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], "OTP sent successfully to your email")

        # Verify DB record exists
        self.assertTrue(OTPVerification.objects.filter(email="test@hrms.com").exists())
        record = OTPVerification.objects.get(email="test@hrms.com")
        self.assertEqual(len(record.otp), 6)
        self.assertFalse(record.is_verified)

    def test_send_otp_nonexistent_email(self):
        data = {
            "email": "fake@hrms.com"
        }
        response = self.client.post('/accounts/send-otp/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_verify_otp_success(self):
        # First send OTP to create the record
        self.client.post('/accounts/send-otp/', {"email": "test@hrms.com"}, format='json')
        record = OTPVerification.objects.get(email="test@hrms.com")

        # Verify with correct OTP
        data = {
            "email": "test@hrms.com",
            "otp": record.otp
        }
        response = self.client.post('/accounts/verify-otp/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check DB state
        record.refresh_from_db()
        self.assertTrue(record.is_verified)

    def test_verify_otp_invalid(self):
        # Send OTP
        self.client.post('/accounts/send-otp/', {"email": "test@hrms.com"}, format='json')

        # Verify with incorrect OTP
        data = {
            "email": "test@hrms.com",
            "otp": "000000"
        }
        response = self.client.post('/accounts/verify-otp/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_success(self):
        # Create verified OTP record
        OTPVerification.objects.create(
            email="test@hrms.com",
            otp="123456",
            is_verified=True
        )

        data = {
            "email": "test@hrms.com",
            "new_password": "new_secure_password"
        }
        response = self.client.post('/accounts/reset-password/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check user password has updated (try login)
        login_data = {
            "username_or_email": "test@hrms.com",
            "password": "new_secure_password"
        }
        login_response = self.client.post('/accounts/login/', login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_response.data)

        # Verification record should be cleaned up/deleted
        self.assertFalse(OTPVerification.objects.filter(email="test@hrms.com").exists())

    def test_reset_password_fails_without_verification(self):
        # Create an unverified OTP record
        OTPVerification.objects.create(
            email="test@hrms.com",
            otp="123456",
            is_verified=False
        )

        data = {
            "email": "test@hrms.com",
            "new_password": "new_secure_password"
        }
        response = self.client.post('/accounts/reset-password/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("OTP has not been verified", response.data['message'])

    def test_auto_create_user_and_credentials_via_signal(self):
        # Delete existing employee to avoid unique constraints if any
        Employee.objects.filter(email="signaluser@hrms.com").delete()
        User.objects.filter(username="signaluser").delete()
        
        # Create employee without a user
        emp = Employee.objects.create(
            name="Signal User",
            email="signaluser@hrms.com",
            phone="1234567890",
            role="EMPLOYEE",
            designation="Developer",
            department="IT",
            joining_date=date.today()
        )
        
        # Verify a User was automatically created and associated
        self.assertIsNotNone(emp.user)
        self.assertEqual(emp.user.email, "signaluser@hrms.com")
        self.assertTrue(User.objects.filter(email="signaluser@hrms.com").exists())

    def test_otp_self_healing_email(self):
        # Create a user with NO email, and an associated Employee with an email
        User.objects.filter(username="noemailuser").delete()
        user_no_email = User.objects.create_user(username="noemailuser", password="password123")
        self.assertEqual(user_no_email.email, "")
        
        Employee.objects.filter(email="healed@hrms.com").delete()
        Employee.objects.create(
            user=user_no_email,
            name="No Email User",
            email="healed@hrms.com",
            phone="1234567890",
            role="EMPLOYEE",
            designation="Developer",
            department="IT",
            joining_date=date.today()
        )
        
        # Initially, User doesn't have the email
        self.assertFalse(User.objects.filter(email="healed@hrms.com").exists())
        
        # Call send-otp
        response = self.client.post('/accounts/send-otp/', {"email": "healed@hrms.com"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # User should now have the email field populated (self-healed!)
        user_no_email.refresh_from_db()
        self.assertEqual(user_no_email.email, "healed@hrms.com")
