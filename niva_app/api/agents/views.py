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
from niva_app.models.dailycalls import DailyCall
from niva_app.api.common.views import BaseAPI
from niva_app.lib.validators import agent_name_validator
from niva_app.models import Agent
from niva_app.api.agents.serializers import InputSerializer
from niva_app.services.pipecat_agent import AgentCallProcessor
from asgiref.sync import sync_to_async, async_to_sync

logger = logging.getLogger(__name__)

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
            required_fields = ['call_id', 'session_id', 'course_id', 'agent_id', 'student_id']
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