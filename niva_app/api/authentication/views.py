import phonenumbers
from django.core.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

from custard_app.api.common.views import OpenAPI, BaseAPI
from custard_app.services.user import create_user, validate_user, activate_user, get_user, reset_password
from custard_app.services.company import CompanyService
from custard_app.api.authentication.exceptions import EmailAlreadyExistsException, OTPExpiredException, InvalidOTPException
from custard_app.services.email import generate_email_otp, verify_email_otp, create_or_get_authentication_token

from .serializers import CreateUserInputSerializer, ActivateUserInputSerializer, LoginViewInputSerializer, SendPasswordResetOTPEmailInputSerializer, ResetPasswordInputSerializer

import logging

from custard_app.lib.utils import get_phone_number_with_country_code
from custard_app.models import Role, RoleType
# from custard_app.services.phone_verification import send_otp, verify_otp
from rest_framework import serializers

logger = logging.getLogger(__name__)


class CreateUser(OpenAPI):
    """
    Create User API

    API to create a new user with the given email and password.
    The user will be assigned the specified role for their company.

    Request:
        email: string
        password: string
        company_name: string
        company_description: string (optional)
        phone_number: string (optional)
        role_type: string (admin/user)

    Response:
        message: string
        company: {
            id: UUID,
            name: string,
            phone_number: string (optional),
            time_zone: string
        }
        temp_email_otp: string
    """
    input_serializer_class = CreateUserInputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()

        try:
            validate_user(email=data["email"])

            # Create company
            company_service = CompanyService()
            company = company_service.create_company(
                name=data["company_name"],
                phone_number=data.get("phone_number"),
                time_zone=data.get("time_zone", "Asia/Kolkata"),
            )

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
                company=company,
            )

            # Generate and store OTP
            otp = generate_email_otp(data["email"])
            logger.info(f"Created user {user.email} with OTP: {otp}")

            # Prepare company details for response
            company_details = {
                "id": str(company.id),
                "name": company.name,
                "phone_number": company.phone_number.phone_number if company.phone_number else None,
                "time_zone": str(company.time_zone),
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
                "message": "User created successfully. Please verify your email to login.",
                "company": company_details,
                "temp_otp": otp,
            },
            status=HTTP_200_OK,
        )


class ActivateUser(OpenAPI):
    """
    Activate User API

    API to activate a user with the given email and otp.

    Request:
        email: string
        otp: string

    Response:
        token: string
    """
    input_serializer_class = ActivateUserInputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()
        email = data["email"]
        otp = data["otp"]

        try:
            verify_email_otp(email, otp)
        except OTPExpiredException:
            self.set_response_message("Verification Code expired")
            return self.get_response_400()
        except InvalidOTPException:
            self.set_response_message("Invalid Verification Code")
            return self.get_response_400()

        user = activate_user(email)

        if user is None:
            self.set_response_message("User not found")
            return self.get_response_400()

        token, _ = create_or_get_authentication_token(user)
        response = {
            "token": token.key,
        }
        return Response(
            data=response,
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


# class SendPasswordResetOTPEmail(OpenAPI):
#     """
#     Send Email with OTP for Password Reset API.

#     API to send an email with OTP for password reset to the user with the given email.

#     Request:
#         email: string

#     Response:
#         message: string
#     """
#     input_serializer_class = SendPasswordResetOTPEmailInputSerializer

#     def post(self, request, *args, **kwargs):
#         data = self.validate_input_data()
#         email = data["email"]

#         try:
#             send_password_reset_otp_email(email)
#         except Exception as e:
#             logger.error(f"Error sending password reset OTP: {str(e)}")
#             return Response(
#                 data={"error": "Failed to send password reset OTP"},
#                 status=HTTP_400_BAD_REQUEST
#             )

#         return Response(
#             data={"message": "Password reset OTP sent successfully"},
#             status=HTTP_200_OK,
#         )


# class ResetPassword(OpenAPI):
#     """
#     Reset Password API

#     API to reset the password for the user with the given email and OTP.

#     Request:
#         email: string
#         otp: string
#         password: string

#     Response:
#         message: string
#     """

#     input_serializer_class = ResetPasswordInputSerializer

#     def post(self, request, *args, **kwargs):
#         data = self.validate_input_data()
#         email = data["email"]
#         otp = data["otp"]
#         password = data["password"]

#         try:
#             reset_password(email, otp, password)
#         except OTPExpiredException:
#             self.set_response_message("Verification Code expired")
#             return self.get_response_400()
#         except InvalidOTPException:
#             self.set_response_message("Invalid Verification Code")
#             return self.get_response_400()
#         except Exception as e:
#             logger.error(f"Error resetting password: {str(e)}")
#             return Response(
#                 data={"error": "Failed to reset password"},
#                 status=HTTP_400_BAD_REQUEST
#             )

#         return Response(
#             data={"message": "Password reset successfully"},
#             status=HTTP_200_OK,
#         )