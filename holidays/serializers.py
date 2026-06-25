from rest_framework import serializers
from .models import Holiday


class HolidaySerializer(serializers.ModelSerializer):

    class Meta:
        model = Holiday
        fields = [
            'id',
            'company',
            'name',
            'date',
            'description',
            'created_at'
        ]
        read_only_fields = ['created_at']
