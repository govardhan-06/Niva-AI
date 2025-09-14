import logging
import secrets
from datetime import timedelta

from typing import Dict, Optional, List

from django.utils import timezone

from app import config
from niva_app.models import User, Role, RoleType, UserStatus

from django.db import transaction
from django.db.models import Q, QuerySet
from django.conf import settings
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature

from rest_framework.exceptions import PermissionDenied, ValidationError

logger = logging.getLogger(__name__)


def get_user(username: str = None, email: str = None) -> Optional[User]:
    """
    Get the user object.

    Parameters:
        username (str): The username of the user.
        email (str): The email of the user.

    Returns:
        User: The user object if found, else None.
    """
    try:
        return User.objects.get(Q(username=username) | Q(email=email))
    except User.DoesNotExist:
        return None


def create_user(username: str, email: str, password: str, role: Role = None) -> User:
    """
    Create a new user.

    Parameters:
        username (str): The username of the user.
        email (str): The email of the user.
        password (str): The password of the user.
        role (Role): The role object.

    Returns:
        User: The created user object.
    """
    user = User()
    user.set_password(password)
    user.username = username
    user.email = email
    user.role = role
    user.status = UserStatus.ACTIVE
    user.save()
    return user


def activate_user(email: str) -> Optional[User]:
    """
    Activate the user.

    Parameters:
        email (str): The email of the user.

    Returns:
        User: The activated user object if found, else None.
    """
    user = User.objects.filter(email=email).first()
    if not user:
        return None

    user.is_active = True
    user.is_email_verified = True
    user.save()
    return user

def validate_user(email: str) -> None:
    """
    Validate that a user with the given email does not already exist.

    Parameters:
        email (str): The email to validate.

    Raises:
        ValidationError: If a user with the email already exists.
    """
    if User.objects.filter(email=email).exists():
        raise ValidationError({"email": "A user with this email already exists."})

def reset_password(email: str, password: str) -> User:
    """
    Reset the user password.

    Parameters:
        email (str): The email of the user.
        password (str): The new password of the user.

    Returns:
        User: The updated user object.

    Raises:
        User.DoesNotExist: If the user does not exist.
    """
    user = User.objects.get(email=email)
    user.set_password(password)
    user.save()
    return user


class UserManagementService:
    @staticmethod
    @transaction.atomic
    def create_user(
        *, creator: User, email: str, password: str, role_type: str
    ) -> User:
        """
        Create a new user.

        Parameters:
            creator (User): The admin user creating this user.
            email (str): The email of the user.
            password (str): The password of the user.
            role_type (str): The role type (e.g., "admin" or "user").

        Returns:
            User: The created user object.

        Raises:
            PermissionDenied: If the creator is not an admin.
        """
        if not creator.is_admin():
            raise PermissionDenied("Only admins can create users")

        # Get or create the role
        role, _ = Role.objects.get_or_create(
            role_type=role_type,
            defaults={
                "name": f"{role_type.title()}",
                "description": f"{role_type.title()} role",
            },
        )

        # Create the user
        user = User.objects.create(
            email=email,
            username=email,
            role=role,
            status=UserStatus.ACTIVE,
        )
        user.set_password(password)
        user.save()
        return user

    @staticmethod
    def get_all_users() -> QuerySet:
        """
        Get all users.

        Returns:
            QuerySet: A queryset containing all users.
        """
        return User.objects.all()

    @staticmethod
    @transaction.atomic
    def update_user(
        *, admin: User, user_id: str, role_type: str
    ) -> User:
        """
        Update the user's role.

        Parameters:
            admin (User): The admin performing the update.
            user_id (str): The ID of the user to update.
            role_type (str): The new role type.

        Returns:
            User: The updated user object.

        Raises:
            PermissionDenied: If the admin is not authorized.
        """
        if not admin.is_admin():
            raise PermissionDenied("Only admins can update users")

        user = User.objects.get(id=user_id)

        # Update role if changed
        if user.role.role_type != role_type:
            role = Role.objects.get(role_type=role_type)
            user.role = role
            user.save()

        return user