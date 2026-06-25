from rest_framework import serializers
from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):

    selfie = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = '__all__'

    def get_selfie(self, obj):

        request = self.context.get('request')

        if obj.selfie:
            return request.build_absolute_uri(
                obj.selfie.url
            )

        return None


class CheckInRequestSerializer(serializers.Serializer):
    selfie = serializers.ImageField(help_text="Selfie image of the employee checking in")