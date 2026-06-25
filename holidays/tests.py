from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date

from employees.models import Employee
from companies.models import Company
from .models import Holiday


class HolidayAPITests(APITestCase):

    def setUp(self):
        # Create companies
        self.company1 = Company.objects.create(name="Company One", email="c1@example.com", address="Addr 1")
        self.company2 = Company.objects.create(name="Company Two", email="c2@example.com", address="Addr 2")

        # Create an Employee user in Company One
        self.employee_user = User.objects.create_user(username="emp_user", password="password")
        self.employee = Employee.objects.create(
            user=self.employee_user,
            company=self.company1,
            name="Employee One",
            email="emp1@example.com",
            phone="1111111111",
            role="EMPLOYEE",
            designation="Developer",
            department="IT",
            joining_date=date.today()
        )

        # Create an HR user in Company One
        self.hr_user = User.objects.create_user(username="hr_user", password="password")
        self.hr = Employee.objects.create(
            user=self.hr_user,
            company=self.company1,
            name="HR Manager",
            email="hr@example.com",
            phone="3333333333",
            role="HR",
            designation="HR Specialist",
            department="HR",
            joining_date=date.today()
        )

        # Create another Employee user in Company Two
        self.other_employee_user = User.objects.create_user(username="other_emp_user", password="password")
        self.other_employee = Employee.objects.create(
            user=self.other_employee_user,
            company=self.company2,
            name="Employee Two",
            email="emp2@example.com",
            phone="2222222222",
            role="EMPLOYEE",
            designation="Designer",
            department="Design",
            joining_date=date.today()
        )

    def test_create_holiday_success_for_hr(self):
        self.client.force_authenticate(user=self.hr_user)

        data = {
            "name": "New Year Day",
            "date": "2027-01-01",
            "description": "Start of the year"
        }

        response = self.client.post('/holidays/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], "New Year Day")
        # Automatically defaults to the creator's company
        self.assertEqual(response.data['company'], self.company1.id)
        self.assertTrue(Holiday.objects.filter(name="New Year Day").exists())

    def test_create_holiday_forbidden_for_employee(self):
        self.client.force_authenticate(user=self.employee_user)

        data = {
            "name": "Employee Day",
            "date": "2027-05-01"
        }

        response = self.client.post('/holidays/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_holidays_list(self):
        # Create global holiday
        h_global = Holiday.objects.create(name="Global Day", date=date(2027, 8, 1))

        # Create company 1 holiday
        h_c1 = Holiday.objects.create(company=self.company1, name="Company 1 Day", date=date(2027, 9, 1))

        # Create company 2 holiday
        h_c2 = Holiday.objects.create(company=self.company2, name="Company 2 Day", date=date(2027, 10, 1))

        # Logged in as Employee One (Company One) -> should see Global Day + Company 1 Day
        self.client.force_authenticate(user=self.employee_user)
        response = self.client.get('/holidays/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        names = [h['name'] for h in response.data]
        self.assertIn("Global Day", names)
        self.assertIn("Company 1 Day", names)
        self.assertNotIn("Company 2 Day", names)

    def test_get_holiday_details(self):
        # Create company 1 holiday
        h_c1 = Holiday.objects.create(company=self.company1, name="Company 1 Day", date=date(2027, 9, 1))

        # Employee One (Company One) can view
        self.client.force_authenticate(user=self.employee_user)
        response = self.client.get(f'/holidays/{h_c1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Employee Two (Company Two) cannot view -> 403 Forbidden
        self.client.force_authenticate(user=self.other_employee_user)
        response = self.client.get(f'/holidays/{h_c1.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_holiday_success_for_hr(self):
        h_c1 = Holiday.objects.create(company=self.company1, name="Company 1 Day", date=date(2027, 9, 1))

        self.client.force_authenticate(user=self.hr_user)
        data = {
            "name": "Updated Day Name"
        }
        response = self.client.put(f'/holidays/{h_c1.id}/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Updated Day Name")

        h_c1.refresh_from_db()
        self.assertEqual(h_c1.name, "Updated Day Name")

    def test_delete_holiday_success_for_hr(self):
        h_c1 = Holiday.objects.create(company=self.company1, name="Company 1 Day", date=date(2027, 9, 1))

        self.client.force_authenticate(user=self.hr_user)
        response = self.client.delete(f'/holidays/{h_c1.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Holiday.objects.filter(id=h_c1.id).exists())
