from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

from rest_framework.decorators import (
    api_view,
    permission_classes,
    parser_classes
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Employee
from drf_spectacular.utils import extend_schema
from .serializers import EmployeeSerializer, EmployeeCreateSerializer, EmployeeUpdateSerializer


@extend_schema(methods=['GET'], responses={200: EmployeeSerializer(many=True)})
@extend_schema(methods=['POST'], request=EmployeeCreateSerializer, responses={201: EmployeeSerializer})
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def employee_list(request):

    if request.method == 'GET':

        employees = Employee.objects.all()

        serializer = EmployeeSerializer(
            employees,
            many=True,
            context={'request': request}
        )

        return Response(serializer.data)

    elif request.method == 'POST':

        serializer = EmployeeCreateSerializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            error_message = None
            if "email" in errors:
                error_message = errors["email"][0]
            else:
                first_field = next(iter(errors))
                error_message = errors[first_field]
                if isinstance(error_message, list):
                    error_message = error_message[0]
                elif isinstance(error_message, dict):
                    first_nested = next(iter(error_message))
                    error_message = error_message[first_nested][0]

            return Response(
                {"message": str(error_message)},
                status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = serializer.validated_data
        email = validated_data.get('email')
        name = validated_data.get('name')
        phone = validated_data.get('phone')
        role = validated_data.get('role')
        designation = validated_data.get('designation')
        department = validated_data.get('department')
        joining_date = validated_data.get('joining_date')

        profile_image = request.FILES.get('profile_image')
        if profile_image:
            from .utils import has_face
            if not has_face(profile_image):
                return Response(
                    {"message": "Image should contain Person face"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Auto-generate a unique username based on the email
        import re
        base_username = email.split('@')[0]
        base_username = re.sub(r'[^a-zA-Z0-9_.-]', '', base_username)
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # Auto-generate a secure random password
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for _ in range(10))

        from django.db import transaction
        from django.core.mail import send_mail

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    password=password
                )

                # Determine the company ID:
                # If the logged-in user has an associated Employee profile with a company, use that.
                # Otherwise, fall back to the company ID provided in the request data.
                company_id = None
                try:
                    requesting_employee = Employee.objects.get(user=request.user)
                    if requesting_employee.company:
                        company_id = requesting_employee.company.id
                except Employee.DoesNotExist:
                    pass

                if not company_id:
                    company_id = request.data.get('company')

                employee = Employee.objects.create(
                    user=user,
                    company_id=company_id,
                    name=name,
                    email=email,
                    phone=phone,
                    role=role,
                    designation=designation,
                    department=department,
                    joining_date=joining_date,
                    profile_image=profile_image
                )

                # Send email to the employee with their credentials
                subject = "Welcome to HRMS - Your Account Credentials"
                email_message = f"Hello {name},\n\nWelcome to HRMS! Your account has been successfully created.\n\nHere are your login credentials:\nUsername: {username}\nPassword: {password}\n\nPlease login and update your password.\n\nBest regards,\nHR Team"
                send_mail(
                    subject=subject,
                    message=email_message,
                    from_email="noreply@hrms.com",
                    recipient_list=[email],
                    fail_silently=False
                )
        except Exception as e:
            return Response(
                {"message": "Failed to create employee.", "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = EmployeeSerializer(
            employee,
            context={'request': request}
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )


@extend_schema(methods=['GET'], responses={200: EmployeeSerializer})
@extend_schema(methods=['PUT'], request=EmployeeUpdateSerializer, responses={200: EmployeeSerializer})
@extend_schema(methods=['DELETE'], responses={204: None})
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def employee_detail(request, pk):

    employee = get_object_or_404(
        Employee,
        pk=pk
    )

    if request.method == 'GET':

        serializer = EmployeeSerializer(
            employee,
            context={'request': request}
        )

        return Response(serializer.data)

    elif request.method == 'PUT':

        profile_image = request.FILES.get('profile_image')
        if profile_image:
            from .utils import has_face
            if not has_face(profile_image):
                return Response(
                    {"message": "Image should contain Person face"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = EmployeeSerializer(
            employee,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            employee_obj = serializer.save()
            if profile_image:
                employee_obj.profile_image = profile_image
                employee_obj.save()

            serializer = EmployeeSerializer(
                employee_obj,
                context={'request': request}
            )

            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    elif request.method == 'DELETE':

        employee.delete()

        return Response(
            {
                "message": "Employee deleted successfully"
            },
            status=status.HTTP_204_NO_CONTENT
        )