from rest_framework import serializers
from .validators import location_name_validator
# from custard_app.models.company import CompanyflowVersion, AgentPromptVersion
from custard_app.models import User

class CreateCompanyInputSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=150, required=True, validators=[location_name_validator]
    )
    address = serializers.CharField(allow_blank=True)
    time_zone = serializers.CharField(required=True)


class DisableInputSerializer(serializers.Serializer):
    disabled_response = serializers.BooleanField(required=True)


class UpdateCompanyAgentInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    prompt = serializers.CharField(required=False)
    is_inbound = serializers.BooleanField(default=False, required=False)
    is_active = serializers.BooleanField(default=True, required=False)
    language = serializers.ChoiceField(
        choices=[('en', 'English'), ('hi', 'Hindi'), ('ml', 'Malayalam'), ('ta', 'Tamil')],
        default='en',
        required=False
    )


class UpdateCompanyInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=True)
    address = serializers.CharField(allow_blank=True)
    time_zone = serializers.CharField(required=True)
    agent = UpdateCompanyAgentInputSerializer(required=False)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class AddCompanyPhoneInputSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    sid = serializers.CharField(required=True)
    account_sid = serializers.CharField(required=True)
    voice_url = serializers.URLField(required=False, allow_null=True)

class UpdateCompanyPhoneInputSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=False)
    sid = serializers.CharField(required=False)
    account_sid = serializers.CharField(required=False)
    voice_url = serializers.URLField(required=False, allow_null=True)