from rest_framework import serializers
from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):

    selfie = serializers.SerializerMethodField()
    checkout_selfie = serializers.SerializerMethodField()
    totalworktime = serializers.SerializerMethodField()

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

    def get_checkout_selfie(self, obj):

        request = self.context.get('request')

        if obj.checkout_selfie:
            return request.build_absolute_uri(
                obj.checkout_selfie.url
            )

        return None

    def get_totalworktime(self, obj):
        if obj.check_in and obj.check_out:
            duration = obj.check_out - obj.check_in
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours:02d}:{minutes:02d}"
        return None


class CheckInRequestSerializer(serializers.Serializer):
    selfie = serializers.ImageField(help_text="Selfie image of the employee checking in")


class CheckOutRequestSerializer(serializers.Serializer):
    checkout_selfie = serializers.ImageField(help_text="Selfie image of the employee checking out")