from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q

from employees.models import Employee
from .models import Holiday
from .serializers import HolidaySerializer


from drf_spectacular.utils import extend_schema


@extend_schema(methods=['GET'], responses={200: HolidaySerializer(many=True)})
@extend_schema(methods=['POST'], request=HolidaySerializer, responses={201: HolidaySerializer})
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def holiday_list(request):

    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return Response(
            {"message": "Employee profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        if employee.company:
            holidays = Holiday.objects.filter(
                Q(company=employee.company) | Q(company__isnull=True)
            ).order_by('date')
        else:
            holidays = Holiday.objects.filter(company__isnull=True).order_by('date')

        serializer = HolidaySerializer(holidays, many=True, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'POST':
        if employee.role not in ['SUPER_ADMIN', 'ADMIN', 'HR']:
            return Response(
                {"message": "You do not have permission to add holidays"},
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data.copy()
        if 'company' not in data and employee.company:
            data['company'] = employee.company.id

        serializer = HolidaySerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['GET'], responses={200: HolidaySerializer})
@extend_schema(methods=['PUT'], request=HolidaySerializer, responses={200: HolidaySerializer})
@extend_schema(methods=['DELETE'], responses={204: None})
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def holiday_detail(request, pk):

    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return Response(
            {"message": "Employee profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    holiday = get_object_or_404(Holiday, pk=pk)

    # Scoping checks for GET
    if request.method == 'GET':
        if holiday.company and employee.company and holiday.company != employee.company:
            if employee.role not in ['SUPER_ADMIN', 'ADMIN', 'HR']:
                return Response(
                    {"message": "You do not have access to this holiday"},
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = HolidaySerializer(holiday, context={'request': request})
        return Response(serializer.data)

    # Write operations require HR/Admin role
    if employee.role not in ['SUPER_ADMIN', 'ADMIN', 'HR']:
        return Response(
            {"message": "You do not have permission to modify holidays"},
            status=status.HTTP_403_FORBIDDEN
        )

    # Additional company check for write operations
    if holiday.company and employee.company and holiday.company != employee.company:
        if employee.role != 'SUPER_ADMIN':
            return Response(
                {"message": "You cannot modify holidays of another company"},
                status=status.HTTP_403_FORBIDDEN
            )

    if request.method == 'PUT':
        serializer = HolidaySerializer(holiday, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        holiday.delete()
        return Response(
            {"message": "Holiday deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )
