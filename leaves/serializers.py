from rest_framework import serializers
from .models import Leave, LeaveDate, LeaveType, LeaveBalance


class LeaveTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = LeaveType
        fields = ['id', 'company', 'name', 'default_annual_quota']


class LeaveBalanceSerializer(serializers.ModelSerializer):

    leave_type_name = serializers.ReadOnlyField(source='leave_type.name')
    employee_name = serializers.ReadOnlyField(source='employee.name')
    remaining_days = serializers.ReadOnlyField()

    class Meta:
        model = LeaveBalance
        fields = [
            'id',
            'employee',
            'employee_name',
            'leave_type',
            'leave_type_name',
            'year',
            'allocated_days',
            'used_days',
            'remaining_days'
        ]
        read_only_fields = ['employee', 'used_days', 'remaining_days']


class LeaveDateSerializer(serializers.ModelSerializer):

    class Meta:
        model = LeaveDate
        fields = ['id', 'date']


class LeaveSerializer(serializers.ModelSerializer):

    dates = LeaveDateSerializer(many=True, read_only=True)
    employee_name = serializers.ReadOnlyField(source='employee.name')
    leave_type_name = serializers.ReadOnlyField(source='leave_type.name')

    class Meta:
        model = Leave
        fields = [
            'id',
            'employee',
            'employee_name',
            'leave_type',
            'leave_type_name',
            'reason',
            'status',
            'total_days',
            'created_at',
            'dates'
        ]
        read_only_fields = [
            'employee',
            'status',
            'total_days',
            'created_at'
        ]


class ApplyLeaveRequestSerializer(serializers.Serializer):
    leave_type = serializers.IntegerField(help_text="Leave Type ID")
    dates = serializers.ListField(child=serializers.DateField(), help_text="List of dates in YYYY-MM-DD format")
    reason = serializers.CharField(help_text="Reason for applying")

