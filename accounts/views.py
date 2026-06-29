from django.shortcuts import render
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from employees.models import Employee


from drf_spectacular.utils import extend_schema
from .serializers import LoginSerializer, LoginResponseSerializer


@extend_schema(
    auth=[],
    request=LoginSerializer,
    responses={200: LoginResponseSerializer}
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):

    email = request.data.get('email')
    password = request.data.get('password')

    username = None
    try:
        employee = Employee.objects.get(email=email)
        if employee.user:
            username = employee.user.username
    except Employee.DoesNotExist:
        try:
            user_obj = User.objects.get(email=email)
            username = user_obj.username
        except User.DoesNotExist:
            pass

    user = authenticate(
        username=username,
        password=password
    )

    if user is None:
        return Response(
            {"message": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    refresh = RefreshToken.for_user(user)

    try:
        employee = Employee.objects.get(user=user)
        from profiles.serializers import ProfileSerializer
        employee_data = ProfileSerializer(employee, context={'request': request}).data
    except Employee.DoesNotExist:
        employee_data = None

    return Response({
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "employee": employee_data
    })


import random
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from .models import OTPVerification
from .serializers import SendOTPSerializer, VerifyOTPSerializer, ResetPasswordSerializer, MessageResponseSerializer


@extend_schema(
    auth=[],
    request=SendOTPSerializer,
    responses={200: MessageResponseSerializer}
)
@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp(request):

    email = request.data.get('email')
    if not email:
        return Response(
            {"message": "Email is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Verify user exists with this email
    if not User.objects.filter(email=email).exists():
        return Response(
            {"message": "User with this email does not exist"},
            status=status.HTTP_404_NOT_FOUND
        )

    # Generate 6-digit OTP
    otp = f"{random.randint(100000, 999999)}"

    # Create or update verification record
    OTPVerification.objects.update_or_create(
        email=email,
        defaults={
            'otp': otp,
            'is_verified': False
        }
    )

    # Send email
    try:
        send_mail(
            subject="Your HRMS Password Reset OTP",
            message=f"Your OTP code is: {otp}. This code is valid for 10 minutes.",
            from_email="noreply@hrms.com",
            recipient_list=[email],
            fail_silently=False
        )
    except Exception as e:
        return Response(
            {
                "message": "Failed to send email",
                "error": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response({"message": "OTP sent successfully to your email"})


@extend_schema(
    auth=[],
    request=VerifyOTPSerializer,
    responses={200: MessageResponseSerializer}
)
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):

    email = request.data.get('email')
    otp = request.data.get('otp')

    if not email or not otp:
        return Response(
            {"message": "Email and OTP are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        record = OTPVerification.objects.get(email=email, otp=otp)
    except OTPVerification.DoesNotExist:
        return Response(
            {"message": "Invalid email or OTP"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check expiration (10 minutes)
    if timezone.now() - record.updated_at > timedelta(minutes=10):
        return Response(
            {"message": "OTP has expired"},
            status=status.HTTP_400_BAD_REQUEST
        )

    record.is_verified = True
    record.save()

    return Response({"message": "OTP verified successfully"})


@extend_schema(
    auth=[],
    request=ResetPasswordSerializer,
    responses={200: MessageResponseSerializer}
)
@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):

    email = request.data.get('email')
    new_password = request.data.get('new_password')

    if not email or not new_password:
        return Response(
            {"message": "Email and new_password are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        record = OTPVerification.objects.get(email=email, is_verified=True)
    except OTPVerification.DoesNotExist:
        return Response(
            {"message": "OTP has not been verified for this email"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check expiration of verification (15 minutes)
    if timezone.now() - record.updated_at > timedelta(minutes=15):
        return Response(
            {"message": "Verification has expired. Please verify OTP again."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Update password for user(s) with this email
    users = User.objects.filter(email=email)
    if not users.exists():
        return Response(
            {"message": "User not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    for user in users:
        user.set_password(new_password)
        user.save()

    # Clean up verification record
    record.delete()

    return Response({"message": "Password updated successfully"})
