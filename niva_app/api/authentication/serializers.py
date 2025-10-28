from rest_framework import serializers
from niva_app.models import RoleType


class CreateUserInputSerializer(serializers.Serializer):
    """
    Input Serializer for CreateUser API

    This serializer is used to validate the input data for the CreateUser API.
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, min_length=8)
    role_type = serializers.ChoiceField(choices=RoleType.choices, required=True)
    
    # Optional fields for student profile creation
    create_student_profile = serializers.BooleanField(required=False, default=False)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.ChoiceField(
        choices=["MALE", "FEMALE", "RATHER_NOT_SAY", "UNKNOWN"],
        required=False,
        default="UNKNOWN"
    )
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    course_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True
    )

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