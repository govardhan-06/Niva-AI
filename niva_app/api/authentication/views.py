import phonenumbers
from django.core.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

from niva_app.api.common.views import OpenAPI, BaseAPI
from niva_app.services.user import create_user, validate_user, activate_user, get_user
from niva_app.api.authentication.exceptions import EmailAlreadyExistsException, OTPExpiredException, InvalidOTPException
from niva_app.services.email import verify_email_otp, create_or_get_authentication_token

from .serializers import CreateUserInputSerializer, ActivateUserInputSerializer, LoginViewInputSerializer

import logging

from niva_app.models import Role, RoleType
from rest_framework import serializers

logger = logging.getLogger(__name__)


class CreateUser(OpenAPI):
    """
    Create User API

    API to create a new user with the given email and password.

    Request:
        email: string
        password: string
        role_type: string (admin/user)

    Response:
        message: string
        user: {
            id: UUID,
            email: string,
            username: string,
            role: string
        }
    """
    input_serializer_class = CreateUserInputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()

        try:
            validate_user(email=data["email"])

            # Get or create role
            role, _ = Role.objects.get_or_create(
                name=data["role_type"].title(),
                defaults={
                    "description": f"{data['role_type'].title()} role",
                    "role_type": data["role_type"]
                }
            )

            # Create user with role
            user = create_user(
                username=data["email"],
                email=data["email"],
                password=data["password"],
                role=role
            )

            logger.info(f"Created active user {user.email}")

            user_data = {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "role": user.role.name if user.role else None
            }

        except EmailAlreadyExistsException as e:
            logger.error("Email already in use: %s", data["email"])
            return Response(
                data={"email": ["Email already in use"]},
                status=HTTP_400_BAD_REQUEST,
            )
        except ValidationError as e:
            logger.error("Validation Error: %s", str(e))
            return Response(data=e.message_dict, status=HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return Response(
                data={"error": "Failed to create user account"},
                status=HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "message": "User created successfully.",
                "user": user_data,
            },
            status=HTTP_200_OK,
        )


class LoginView(OpenAPI):
    """
    Login API

    API to login a user with the given email and password.

    Request:
        email: string
        password: string

    Response:
        token: string
    """
    input_serializer_class = LoginViewInputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()
        email = data["email"]
        password = data["password"]
        
        user = get_user(email=email)
        if not user:
            return Response(
                data={
                    "email": [
                        "User is not registered",
                    ],
                },
                status=HTTP_404_NOT_FOUND,
            )
        if not user.check_password(password):
            return Response(
                data={"password": ["Invalid password"]},
                status=HTTP_400_BAD_REQUEST,
            )

        token, _ = create_or_get_authentication_token(user)
        response = {
            "token": token.key,
        }
        return Response(
            data=response,
            status=HTTP_200_OK,
        )