from rest_framework import serializers
from employees.models import Employee
from django.contrib.auth.models import User


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    profile_image = serializers.SerializerMethodField()
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id',
            'username',
            'name',
            'email',
            'phone',
            'role',
            'designation',
            'department',
            'joining_date',
            'profile_image',
            'company',
            'company_name'
        ]
        read_only_fields = ['id', 'role', 'designation', 'department', 'joining_date', 'company', 'company_name']

    def get_profile_image(self, obj):
        request = self.context.get('request')
        if obj.profile_image:
            return request.build_absolute_uri(obj.profile_image.url)
        return None


class ProfileUpdateSerializer(serializers.ModelSerializer):
    profile_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Employee
        fields = [
            'name',
            'email',
            'phone',
            'profile_image'
        ]

    def update(self, instance, validated_data):
        email = validated_data.get('email')
        if email:
            user = instance.user
            if user:
                user.email = email
                user.save()
        return super().update(instance, validated_data)
