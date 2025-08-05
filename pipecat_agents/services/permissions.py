from rest_framework import permissions

class IsMicroserviceAuthenticated(permissions.BasePermission):
    """
    Permission class for microservice authentication.
    Allows access only if the request is authenticated via MicroserviceAuthentication.
    """
    
    def has_permission(self, request, view):
        # Check if request has been authenticated by MicroserviceAuthentication
        return hasattr(request, 'auth') and request.auth is not None


class AllowHealthCheck(permissions.BasePermission):
    """
    Permission class that allows unauthenticated access to health check endpoints.
    """
    
    def has_permission(self, request, view):
        return True