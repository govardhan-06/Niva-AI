from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from rest_framework import serializers
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from django.utils import timezone
from datetime import timedelta
import base64
import logging
from rest_framework.views import APIView
from custard_app.models.dailycalls import DailyCall
from custard_app.api.common.views import BaseAPI
from custard_app.lib.validators import agent_name_validator
from custard_app.models import Agent
from custard_app.api.agents.serializers import InputSerializer
from custard_app.services.pipecat_agent import AgentCallProcessor
from asgiref.sync import sync_to_async, async_to_sync

logger = logging.getLogger(__name__)

class ListAgents(BaseAPI):
    """
    List all agents for the user's company.
    
    Returns:
        List of agents with their details
    """
    def get(self, request, *args, **kwargs):
        user = self.get_user()
        company = user.company

        agents = Agent.objects.filter(company=company)
        response = []
        
        for agent in agents:
            response.append({
                "id": agent.id,
                "name": agent.name,
                "is_active": agent.is_active,
                "created_at": agent.created_at,
                "company": agent.company.id,
                "is_inbound": agent.is_inbound,
                "language": agent.language,
                "prompt": agent.prompt,
                "is_company_inbound_agent": company.inbound_agent == agent,
                "is_company_outbound_agent": company.outbound_agent == agent,
            })

        return Response(response, status=HTTP_200_OK)


class GetAgent(BaseAPI):
    """
    Get details of a specific agent.
    
    Args:
        agent_id: UUID of the agent
        
    Returns:
        Agent details
    """
    def get(self, request, *args, **kwargs):
        agent_id = kwargs.get("agent_id")
        user = self.get_user()
        
        agent = get_object_or_404(Agent, id=agent_id, company=user.company)
        company = user.company

        response = {
            "id": agent.id,
            "name": agent.name,
            "is_inbound": agent.is_inbound,
            "is_active": agent.is_active,
            "company": agent.company.id,
            "language": agent.language,
            "prompt": agent.prompt,
            "is_company_inbound_agent": company.inbound_agent == agent,
            "is_company_outbound_agent": company.outbound_agent == agent,
        }
        return Response(response, status=HTTP_200_OK)


class UpdateAgent(BaseAPI):
    """
    Update an agent's details.
    
    Args:
        agent_id: UUID of the agent
        
    Request Body:
        name: string (optional)
        prompt: string (optional)
        language: string (optional) - choices: en, hi, ml, ta
        is_active: boolean (optional)
    """
    class InputSerializer(serializers.Serializer):
        name = serializers.CharField(validators=[agent_name_validator], required=False)
        prompt = serializers.CharField(required=False, allow_blank=True)
        language = serializers.ChoiceField(choices=Agent.LANGUAGE_CHOICES, required=False)
        is_active = serializers.BooleanField(required=False)

    input_serializer_class = InputSerializer

    def post(self, request, *args, **kwargs):
        agent_id = kwargs.get("agent_id")
        user = self.get_user()
        data = self.validate_input_data()
        
        agent = get_object_or_404(Agent, id=agent_id, company=user.company)
        
        # Update only provided fields
        for field, value in data.items():
            if value is not None:
                setattr(agent, field, value)
        
        agent.save()

        # If agent is deactivated, remove it from company references
        company = user.company
        if 'is_active' in data and not data['is_active']:
            if company.inbound_agent == agent:
                company.inbound_agent = None
            if company.outbound_agent == agent:
                company.outbound_agent = None
            company.save()
        # If agent is reactivated, set it back based on its type
        elif 'is_active' in data and data['is_active']:
            if agent.is_inbound:
                company.inbound_agent = agent
            else:
                company.outbound_agent = agent
            company.save()

        response = {
            "id": agent.id,
            "name": agent.name,
            "is_inbound": agent.is_inbound,
            "is_active": agent.is_active,
            "company": agent.company.id,
            "language": agent.language,
            "prompt": agent.prompt,
        }
        return Response(response, status=HTTP_200_OK)


class CreateAgent(BaseAPI):
    """
    Create a new agent.
    
    Request Body:
        name: string
        prompt: string (optional)
        language: string (optional) - choices: en, hi, ml, ta
        is_inbound: boolean (optional)
        is_active: boolean (optional)
    """

    input_serializer_class = InputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()
        user = self.get_user()

        # Create agent
        agent = Agent.objects.create(
            name=data["name"],
            prompt=data.get("prompt", "Hello, how can I help you?"),
            language=data.get("language", "en"),
            is_inbound=data.get("is_inbound", False),
            is_active=data.get("is_active", True),
            company=user.company,
        )

        # Update company's agent references
        company = user.company
        if data.get("is_inbound", False):
            company.inbound_agent = agent
        else:
            company.outbound_agent = agent
        company.save()

        response = {
            "id": agent.id,
            "name": agent.name,
            "is_inbound": agent.is_inbound,
            "is_active": agent.is_active,
            "company": agent.company.id,
            "language": agent.language,
            "prompt": agent.prompt,
        }
        return Response(response, status=HTTP_200_OK)


class DisableAgent(BaseAPI):
    """
    Disable or enable an agent.
    """
    class InputSerializer(serializers.Serializer):
        disabled = serializers.BooleanField(required=True)

    input_serializer_class = InputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()
        agent_id = kwargs.get("agent_id")
        user = self.get_user()

        # Fetch the agent and ensure it belongs to the user's company
        agent = get_object_or_404(
            Agent,
            id=agent_id,
            company=user.company
        )

        # Toggle the agent's `is_active` status
        agent.is_active = not data["disabled"]
        agent.save()

        # Update company's agent references
        company = user.company
        if data["disabled"]:
            # Remove agent from company references when disabled
            if company.inbound_agent == agent:
                company.inbound_agent = None
            if company.outbound_agent == agent:
                company.outbound_agent = None
        else:
            # Set agent back to company references when enabled
            if agent.is_inbound:
                company.inbound_agent = agent
            else:
                company.outbound_agent = agent
        company.save()

        response = {
            "id": agent.id,
            "name": agent.name,
            "is_active": agent.is_active,
            "company": agent.company.id,
            "message": f"Agent '{agent.name}' is now {'disabled' if data['disabled'] else 'enabled'}."
        }
        return Response(response, status=HTTP_200_OK)

class CallProcessorStatus(BaseAPI):
    """
    Get status and statistics of call processing
    """
    authentication_classes = []
    permission_classes = []
    
    def get(self, request, *args, **kwargs):
        """
        Return call processing statistics and system status
        """
        try:            
            now = timezone.now()
            last_24h = now - timedelta(hours=24)
            
            total_calls = DailyCall.objects.count()
            recent_calls = DailyCall.objects.filter(created_at__gte=last_24h).count()
            calls_with_recordings = DailyCall.objects.exclude(recording_url='').count()
            calls_with_customers = DailyCall.objects.filter(customer__isnull=False).count()
            
            return Response({
                "status": "healthy",
                "statistics": {
                    "total_calls": total_calls,
                    "calls_last_24h": recent_calls,
                    "calls_with_recordings": calls_with_recordings,
                    "calls_with_customers": calls_with_customers,
                    "recording_success_rate": round((calls_with_recordings / total_calls * 100), 2) if total_calls > 0 else 0
                },
                "services": {
                    "gcp_storage": "operational",
                    "database": "operational",
                    "customer_processor": "operational"
                },
                "timestamp": now.isoformat()
            }, status=HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting call processor status: {e}")
            return Response({
                "status": "error",
                "error": str(e),
                "timestamp": timezone.now().isoformat()
            }, status=HTTP_500_INTERNAL_SERVER_ERROR)

class ProcessPostCallDataView(APIView):
    """
    Class-based view for handling post-call data processing.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        """Health check endpoint."""
        return Response({
            "status": "healthy",
            "service": "post-call-processor",
            "message": "Post-call data processing service is running"
        }, status=HTTP_200_OK)

    def post(self, request):
        """Process post-call data."""
        try:
            logger.info(f"Received post-call data for call {request.data.get('call_id')}")
            
            # Validate required fields
            required_fields = ['call_id', 'session_id', 'company_id', 'agent_id']
            for field in required_fields:
                if not request.data.get(field):
                    return Response({
                        "success": False,
                        "error": f"Missing required field: {field}",
                        "message": "Invalid request data"
                    }, status=HTTP_400_BAD_REQUEST)
            
            # Process the data using AgentCallProcessor with proper async-to-sync conversion
            result = async_to_sync(AgentCallProcessor.process_post_call_data)(request.data)
            
            if result.get("success"):
                logger.info(f"Successfully processed post-call data for call {request.data['call_id']}")
                return Response(result, status=HTTP_200_OK)
            else:
                logger.error(f"Failed to process post-call data: {result}")
                return Response(result, status=HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Unexpected error in process_post_call_data endpoint: {e}")
            return Response({
                "success": False,
                "error": str(e),
                "message": "Failed to process post-call data"
            }, status=HTTP_500_INTERNAL_SERVER_ERROR)