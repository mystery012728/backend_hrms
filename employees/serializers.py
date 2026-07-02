from rest_framework import serializers
from .models import Employee


class EmployeeSerializer(serializers.ModelSerializer):

    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = '__all__'

    def get_profile_image(self, obj):

        request = self.context.get('request')

        if obj.profile_image:
            return request.build_absolute_uri(
                obj.profile_image.url
            )

        return None


class EmployeeCreateSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField()
    role = serializers.ChoiceField(choices=Employee.ROLE_CHOICES, default='EMPLOYEE')
    designation = serializers.CharField()
    department = serializers.CharField()
    joining_date = serializers.DateField()
    profile_image = serializers.ImageField(required=False, allow_null=True)

    def validate_email(self, value):
        if Employee.objects.filter(email=value).exists():
            raise serializers.ValidationError("An employee with this email already exists.")
        return value


class EmployeeUpdateSerializer(serializers.ModelSerializer):
    profile_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Employee
        fields = [
            'name',
            'email',
            'phone',
            'role',
            'designation',
            'department',
            'joining_date',
            'profile_image'
        ]