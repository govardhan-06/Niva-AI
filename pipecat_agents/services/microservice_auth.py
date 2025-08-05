import os
from django.conf import settings
from rest_framework import authentication
from rest_framework import exceptions

class MicroserviceAuthentication(authentication.BaseAuthentication):
    """
    Token-based authentication for microservice-to-microservice communication.
    Uses the shared PIPECAT_BOT_API_TOKEN for validation.
    """
    
    def authenticate(self, request):
        token = self.get_token_from_request(request)
        
        if not token:
            return None
            
        if not self.is_valid_token(token):
            raise exceptions.AuthenticationFailed('Invalid microservice token')
            
        # Return a tuple of (user, auth) - we can use None for user since this is service-to-service
        return (None, token)
    
    def get_token_from_request(self, request):
        """Extract token from Authorization header or query parameter"""
        # Check Authorization header first
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header.split(' ')[1]
            
        # Check for token in request body for POST requests
        if hasattr(request, 'data') and 'token' in request.data:
            return request.data['token']
            
        # Check query parameters
        return request.GET.get('token')
    
    def is_valid_token(self, token):
        """Validate the token against the configured PIPECAT_BOT_API_TOKEN"""
        expected_token = getattr(settings, 'PIPECAT_BOT_API_TOKEN', os.getenv('PIPECAT_BOT_API_TOKEN'))
        return token == expected_token
    
    def authenticate_header(self, request):
        """Return the authentication header for 401 responses"""
        return 'Bearer'