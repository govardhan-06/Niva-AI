import logging
from rest_framework import status
from rest_framework.response import Response
from django.db import transaction
from django.shortcuts import get_object_or_404

from custard_app.api.common.views import BaseAPI
from custard_app.api.user.serializers import (
    CurrentUserDetailOutputSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    UserListSerializer
)
from custard_app.models import User, Role, RoleType, UserStatus

logger = logging.getLogger(__name__)

def create_error_response(status_code, message, errors=None):
    """Helper function to create consistent error responses"""
    return Response(
        {
            "code": status_code,
            "message": message,
            "success": False,
            "data": None,
            "errors": errors or {}
        },
        status=status_code
    )

class CurrentUserData(BaseAPI):
    def get(self, request, *args, **kwargs):
        """Get current user's details"""
        try:
            user = self.get_user()
            serializer = CurrentUserDetailOutputSerializer(user)
            return Response(
                data=serializer.data,
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error retrieving current user data: {str(e)}")
            return create_error_response(
                status.HTTP_400_BAD_REQUEST,
                "Failed to retrieve user data"
            )

class UserManagementView(BaseAPI):
    def get(self, request):
        """List all users in the company"""
        if not request.user.is_admin():
            return create_error_response(
                status.HTTP_403_FORBIDDEN,
                "Permission denied"
            )

        users = User.objects.filter(company=request.user.company)
        serializer = UserListSerializer(users, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create a new user"""
        if not request.user.is_admin():
            return create_error_response(
                status.HTTP_403_FORBIDDEN,
                "Permission denied"
            )

        serializer = UserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return create_error_response(
                status.HTTP_400_BAD_REQUEST,
                "Invalid input data",
                serializer.errors
            )

        try:
            with transaction.atomic():
                # Check if user already exists for this company
                if User.objects.filter(email=serializer.validated_data['email'], company=request.user.company).exists():
                    return create_error_response(
                        status.HTTP_400_BAD_REQUEST,
                        "User with this email already exists in this company"
                    )

                # Get or create role
                role, _ = Role.objects.get_or_create(
                    role_type=serializer.validated_data['role_type'],
                    defaults={
                        "name": f"{request.user.company.name} {serializer.validated_data['role_type']}",
                        "description": f"{serializer.validated_data['role_type']} role for {request.user.company.name}"
                    }
                )

                # Create user
                user = User.objects.create(
                    email=serializer.validated_data['email'],
                    username=serializer.validated_data['email'],
                    company=request.user.company,
                    role=role,
                    first_name=serializer.validated_data.get('first_name', ''),
                    last_name=serializer.validated_data.get('last_name', ''),
                    phone_number=serializer.validated_data.get('phone_number', ''),
                    is_active=True
                )
                user.set_password(serializer.validated_data['password'])
                user.save()

                return Response(
                    UserListSerializer(user).data,
                    status=status.HTTP_201_CREATED
                )

        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return create_error_response(
                status.HTTP_400_BAD_REQUEST,
                "Failed to create user"
            )

class UserDetailView(BaseAPI):
    def get(self, request, user_id):
        """Get user details"""
        if not request.user.is_admin():
            return create_error_response(
                status.HTTP_403_FORBIDDEN,
                "Permission denied"
            )

        user = get_object_or_404(User, id=user_id, company=request.user.company)
        serializer = UserListSerializer(user)
        return Response(serializer.data)

    def put(self, request, user_id):
        """Update user details"""
        if not request.user.is_admin():
            return create_error_response(
                status.HTTP_403_FORBIDDEN,
                "Permission denied"
            )

        user = get_object_or_404(User, id=user_id, company=request.user.company)
        serializer = UserUpdateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return create_error_response(
                status.HTTP_400_BAD_REQUEST,
                "Invalid input data",
                serializer.errors
            )

        try:
            with transaction.atomic():
                # Check if email is being changed and if it's already in use
                if 'email' in serializer.validated_data and serializer.validated_data['email'] != user.email:
                    if User.objects.filter(email=serializer.validated_data['email'], company=request.user.company).exists():
                        return create_error_response(
                            status.HTTP_400_BAD_REQUEST,
                            "User with this email already exists in this company"
                        )

                # Update role if changed
                if 'role_type' in serializer.validated_data:
                    role, _ = Role.objects.get_or_create(
                        role_type=serializer.validated_data['role_type'],
                        defaults={
                            "name": f"{request.user.company.name} {serializer.validated_data['role_type']}",
                            "description": f"{serializer.validated_data['role_type']} role for {request.user.company.name}"
                        }
                    )
                    user.role = role

                # Update other fields
                if 'email' in serializer.validated_data:
                    user.email = serializer.validated_data['email']
                    user.username = serializer.validated_data['email']
                if 'status' in serializer.validated_data:
                    user.is_active = serializer.validated_data['status'] == UserStatus.ACTIVE
                if 'first_name' in serializer.validated_data:
                    user.first_name = serializer.validated_data['first_name']
                if 'last_name' in serializer.validated_data:
                    user.last_name = serializer.validated_data['last_name']
                if 'phone_number' in serializer.validated_data:
                    user.phone_number = serializer.validated_data['phone_number']
                if 'password' in serializer.validated_data:
                    user.set_password(serializer.validated_data['password'])

                user.save()
                return Response(UserListSerializer(user).data)

        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            return create_error_response(
                status.HTTP_400_BAD_REQUEST,
                "Failed to update user"
            )

    def delete(self, request, user_id):
        """Deactivate user"""
        if not request.user.is_admin():
            return create_error_response(
                status.HTTP_403_FORBIDDEN,
                "Permission denied"
            )

        user = get_object_or_404(User, id=user_id, company=request.user.company)
        user.is_active = False
        user.save()
        
        return Response(status=status.HTTP_204_NO_CONTENT)