from rest_framework import serializers
from custard_app.lib.validators import agent_name_validator
from custard_app.models import Agent

class InputSerializer(serializers.Serializer):
    name = serializers.CharField(validators=[agent_name_validator])
    prompt = serializers.CharField(required=False, allow_blank=True)
    language = serializers.ChoiceField(choices=Agent.LANGUAGE_CHOICES, required=False)
    is_inbound = serializers.BooleanField(required=False, default=False)
    is_active = serializers.BooleanField(required=False, default=True)