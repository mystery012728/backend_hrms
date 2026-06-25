from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from datetime import datetime

from employees.models import Employee
from .models import Leave, LeaveDate, LeaveType, LeaveBalance
from drf_spectacular.utils import extend_schema
from .serializers import LeaveSerializer, LeaveTypeSerializer, LeaveBalanceSerializer, ApplyLeaveRequestSerializer


@extend_schema(
    request=ApplyLeaveRequestSerializer,
    responses={201: LeaveSerializer}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_leave(request):

    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return Response(
            {"message": "Employee profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    leave_type_id = request.data.get('leave_type')
    dates = request.data.get('dates')
    reason = request.data.get('reason')

    if not leave_type_id:
        return Response(
            {"message": "leave_type (id) is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    leave_type = get_object_or_404(LeaveType, pk=leave_type_id)

    if not dates:
        return Response(
            {"message": "dates (array of dates) is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not isinstance(dates, list):
        return Response(
            {"message": "dates must be a list/array"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not reason:
        return Response(
            {"message": "reason is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate each date format YYYY-MM-DD
    parsed_dates = []
    current_year = timezone.now().year
    for d in dates:
        try:
            parsed_date = datetime.strptime(str(d), '%Y-%m-%d').date()
            parsed_dates.append(parsed_date)
            # Use the year from dates to ensure proper annual balancing, or default to current year
            current_year = parsed_date.year
        except ValueError:
            return Response(
                {"message": f"Invalid date format: {d}. Expected format: YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )

    # Check for overlapping leaves for this employee
    for d in parsed_dates:
        overlap_exists = LeaveDate.objects.filter(
            leave__employee=employee,
            leave__status__in=['PENDING', 'ACCEPTED'],
            date=d
        ).exists()
        if overlap_exists:
            return Response(
                {"message": f"You have already applied for leave on {d}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    # Fetch or auto-initialize leave balance for this employee, type, and year
    balance, created = LeaveBalance.objects.get_or_create(
        employee=employee,
        leave_type=leave_type,
        year=current_year,
        defaults={
            'allocated_days': leave_type.default_annual_quota,
            'used_days': 0
        }
    )

    total_days = len(parsed_dates)
    if total_days > balance.remaining_days:
        return Response(
            {"message": f"Insufficient leave balance. Remaining: {balance.remaining_days}, Requested: {total_days}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create the Leave object
    leave = Leave.objects.create(
        employee=employee,
        leave_type=leave_type,
        reason=reason,
        total_days=total_days
    )

    # Create LeaveDate objects
    for d in parsed_dates:
        LeaveDate.objects.create(leave=leave, date=d)

    serializer = LeaveSerializer(leave, context={'request': request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(
    responses={200: LeaveSerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def leave_list(request):

    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return Response(
            {"message": "Employee profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # Scoping: Employees see only their own leaves. Admins/HR/Super Admins see all leaves.
    if employee.role in ['SUPER_ADMIN', 'ADMIN', 'HR']:
        leaves = Leave.objects.all().order_by('-created_at')
    else:
        leaves = Leave.objects.filter(employee=employee).order_by('-created_at')

    serializer = LeaveSerializer(leaves, many=True, context={'request': request})
    return Response(serializer.data)


@extend_schema(
    responses={200: LeaveSerializer}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def leave_detail(request, pk):

    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return Response(
            {"message": "Employee profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    leave = get_object_or_404(Leave, pk=pk)

    # Scoping: Standard employee can only see their own leave detail
    if employee.role not in ['SUPER_ADMIN', 'ADMIN', 'HR'] and leave.employee != employee:
        return Response(
            {"message": "You do not have permission to view this leave detail"},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = LeaveSerializer(leave, context={'request': request})
    return Response(serializer.data)


@extend_schema(
    request=None,
    responses={200: LeaveSerializer}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_leave(request, pk):

    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return Response(
            {"message": "Employee profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    if employee.role not in ['SUPER_ADMIN', 'ADMIN', 'HR']:
        return Response(
            {"message": "You do not have permission to accept leaves"},
            status=status.HTTP_403_FORBIDDEN
        )

    leave = get_object_or_404(Leave, pk=pk)
    
    # If already accepted, do nothing
    if leave.status == 'ACCEPTED':
        serializer = LeaveSerializer(leave, context={'request': request})
        return Response(serializer.data)

    # Ensure leave type is associated to perform balance check
    if leave.leave_type:
        year = leave.created_at.year if leave.created_at else timezone.now().year
        # Also check in leave dates for the year
        first_date = leave.dates.first()
        if first_date:
            year = first_date.date.year

        balance, created = LeaveBalance.objects.get_or_create(
            employee=leave.employee,
            leave_type=leave.leave_type,
            year=year,
            defaults={
                'allocated_days': leave.leave_type.default_annual_quota,
                'used_days': 0
            }
        )

        if leave.total_days > balance.remaining_days:
            return Response(
                {"message": f"Cannot accept leave. Insufficient remaining balance ({balance.remaining_days} days)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Deduct balance
        balance.used_days += leave.total_days
        balance.save()

    leave.status = 'ACCEPTED'
    leave.save()

    serializer = LeaveSerializer(leave, context={'request': request})
    return Response(serializer.data)


@extend_schema(
    request=None,
    responses={200: LeaveSerializer}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_leave(request, pk):

    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return Response(
            {"message": "Employee profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    if employee.role not in ['SUPER_ADMIN', 'ADMIN', 'HR']:
        return Response(
            {"message": "You do not have permission to reject leaves"},
            status=status.HTTP_403_FORBIDDEN
        )

    leave = get_object_or_404(Leave, pk=pk)
    
    # If transitioning from ACCEPTED to REJECTED, refund the leave days
    if leave.status == 'ACCEPTED' and leave.leave_type:
        year = leave.created_at.year if leave.created_at else timezone.now().year
        first_date = leave.dates.first()
        if first_date:
            year = first_date.date.year

        try:
            balance = LeaveBalance.objects.get(
                employee=leave.employee,
                leave_type=leave.leave_type,
                year=year
            )
            balance.used_days = max(0, balance.used_days - leave.total_days)
            balance.save()
        except LeaveBalance.DoesNotExist:
            pass

    leave.status = 'REJECTED'
    leave.save()

    serializer = LeaveSerializer(leave, context={'request': request})
    return Response(serializer.data)


@extend_schema(methods=['GET'], responses={200: LeaveTypeSerializer(many=True)})
@extend_schema(methods=['POST'], request=LeaveTypeSerializer, responses={201: LeaveTypeSerializer})
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def leave_type_list(request):

    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return Response(
            {"message": "Employee profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        if employee.company:
            types = LeaveType.objects.filter(
                Q(company=employee.company) | Q(company__isnull=True)
            )
        else:
            types = LeaveType.objects.filter(company__isnull=True)
        serializer = LeaveTypeSerializer(types, many=True, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'POST':
        if employee.role not in ['SUPER_ADMIN', 'ADMIN', 'HR']:
            return Response(
                {"message": "You do not have permission to add leave types"},
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data.copy()
        if 'company' not in data and employee.company:
            data['company'] = employee.company.id

        serializer = LeaveTypeSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    responses={200: LeaveBalanceSerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def leave_balance_list(request):

    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return Response(
            {"message": "Employee profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # Scoping: Employees see their own. HR/Admin see all.
    if employee.role in ['SUPER_ADMIN', 'ADMIN', 'HR']:
        balances = LeaveBalance.objects.all()
    else:
        balances = LeaveBalance.objects.filter(employee=employee)

    serializer = LeaveBalanceSerializer(balances, many=True, context={'request': request})
    return Response(serializer.data)
