"""
Module: niva_app.services.email

This module contains the email service functions. These functions are used to send emails to the users.

Functions:
    - verify_email_otp: Verify the OTP entered by the user.
    - send_mail: Send an email to the user.
    - create_or_get_authentication_token: Create or get the authentication token for the user.
"""

from django.template.loader import render_to_string
from typing import Tuple, Dict, Optional, Any
from rest_framework.authtoken.models import Token

from niva_app.lib.utils import create_4_digit_otp
from niva_app.api.authentication.exceptions import OTPExpiredException, InvalidOTPException

from niva_app.models import User


def verify_email_otp(email: str, otp: str):
    """
    Verify the OTP entered by the user.

    Args:
        email (str): Email address of the user.
        otp (str): OTP entered by the user.

    Raises:
        OTPExpiredException: If the OTP is expired.
        InvalidOTPException: If the OTP is invalid.

    Returns:
        None
    """
    otp_obj = EmailVerificationOTP.objects.filter(email=email).first()
    if otp_obj:
        if otp_obj.is_otp_expired():
            otp_obj.delete()
            raise OTPExpiredException("OTP expired")
        if otp_obj.otp != otp:
            raise InvalidOTPException("Invalid OTP")
    else:
        raise OTPExpiredException("OTP expired")

def create_or_get_authentication_token(user: User) -> Tuple[Token, bool]:
    """
    Create or get the authentication token for the user.

    Args:
        user (User): User object.

    Returns:
        Tuple[Token, bool]: Token object and a boolean indicating whether the token was created or not.
    """
    token, created = Token.objects.get_or_create(user=user)
    return token, created
