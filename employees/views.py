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

        username = request.data.get('username')
        password = request.data.get('password')

        profile_image = request.FILES.get('profile_image')
        if profile_image:
            from .utils import has_face
            if not has_face(profile_image):
                return Response(
                    {"message": "Image should contain Person face"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        user = User.objects.create_user(
            username=username,
            password=password
        )

        employee = Employee.objects.create(
            user=user,
            company_id=request.data.get('company'),
            name=request.data.get('name'),
            email=request.data.get('email'),
            phone=request.data.get('phone'),
            role=request.data.get('role'),
            designation=request.data.get('designation'),
            department=request.data.get('department'),
            joining_date=request.data.get('joining_date'),
            profile_image=profile_image
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