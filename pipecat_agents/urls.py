"""
URL configuration for pipecat_agents API endpoints.
"""
from django.urls import path
from pipecat_agents.api.views import (
    HealthCheckView,
    VoiceCallView,
    ActiveCallsView,
    StopVoiceCallView,
)

agent_routes = [
    path('health/', HealthCheckView.as_view(), name='health_check'),
    path('voice-call/', VoiceCallView.as_view(), name='handle_voice_call'),
    path('active-calls/', ActiveCallsView.as_view(), name='get_active_calls'),
    path('stop-call/', StopVoiceCallView.as_view(), name='stop_voice_call'),
]

