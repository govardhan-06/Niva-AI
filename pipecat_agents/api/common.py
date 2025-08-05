import logging
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse

from pipecat_agents.services.microservice_auth import MicroserviceAuthentication
from pipecat_agents.services.permissions import IsMicroserviceAuthenticated, AllowHealthCheck

logger = logging.getLogger(__name__)

class BaseAPIView(APIView):
    """Base API view with common functionality for all pipecat endpoints"""
    
    def handle_exception(self, exc):
        """Global exception handling for all API views"""
        logger.exception(f"API Error in {self.__class__.__name__}: {exc}")
        return Response({
            "success": False,
            "error": str(exc)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AuthenticatedAPIView(BaseAPIView):
    """Base view for authenticated microservice endpoints"""
    authentication_classes = [MicroserviceAuthentication]
    permission_classes = [IsMicroserviceAuthenticated]


class PublicAPIView(BaseAPIView):
    """Base view for public endpoints (like health checks)"""
    authentication_classes = []
    permission_classes = [AllowHealthCheck]