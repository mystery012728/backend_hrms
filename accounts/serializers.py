from rest_framework import serializers

class LoginSerializer(serializers.Serializer):
    username_or_email = serializers.CharField()
    password = serializers.CharField()


from profiles.serializers import ProfileSerializer

class LoginResponseSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()
    employee = ProfileSerializer(allow_null=True)


class SendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text="Email of the user requesting OTP")


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text="Email of the user verifying OTP")
    otp = serializers.CharField(max_length=6, help_text="6-digit One-Time Password")


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text="Email of the user resetting password")
    new_password = serializers.CharField(help_text="New password to set")


class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField()