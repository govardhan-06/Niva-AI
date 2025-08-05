from rest_framework import serializers
from custard_app.models import RoleType


class CreateUserInputSerializer(serializers.Serializer):
    """
    Input Serializer for CreateUser API

    This serializer is used to validate the input data for the CreateUser API.
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, min_length=8)
    company_name = serializers.CharField(required=True)
    company_description = serializers.CharField(required=False)
    phone_number = serializers.CharField(required=False)
    role_type = serializers.ChoiceField(choices=RoleType.choices, required=True)


class ActivateUserInputSerializer(serializers.Serializer):
    """
    Input Serializer for ActivateUser API

    This serializer is used to validate the input data for the ActivateUser API.
    """

    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True)


class LoginViewInputSerializer(serializers.Serializer):
    """
    Input Serializer for LoginView API

    This serializer is used to validate the input data for the LoginView API.
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)


class SendPasswordResetOTPEmailInputSerializer(serializers.Serializer):
    """
    Input Serializer for SendPasswordResetOTPEmail API

    This serializer is used to validate the input data for the SendPasswordResetOTPEmail API.
    """

    email = serializers.EmailField(required=True)


class ResetPasswordInputSerializer(serializers.Serializer):
    """
    Input Serializer for ResetPassword API

    This serializer is used to validate the input data for the ResetPassword API.
    """

    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True)
    password = serializers.CharField(required=True, min_length=8)
