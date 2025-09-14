"""
Module: niva_app.api.authentication.exceptions

This file contains custom exceptions for the authentication routes.
The exceptions are used to handle errors that occur during the authentication process.

For example, if a user tries to create an account with an email that already exists in the database, an `EmailAlreadyExistsException` is raised.

Exceptions:
    - EmailAlreadyExistsException: Raised when a user tries to create an account with an email that already exists in the database.
    - OTPExpiredException: Raised when an OTP has expired.
    - InvalidOTPException: Raised when an invalid OTP is provided.
"""

from django.core.exceptions import ValidationError


class EmailAlreadyExistsException(ValidationError):
    message = "Email already exists"


class OTPExpiredException(ValidationError):
    message = "OTP Expired"


class InvalidOTPException(ValidationError):
    message = "Invalid OTP"