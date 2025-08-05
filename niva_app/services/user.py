import logging
import secrets
from datetime import timedelta

from typing import Dict, Optional, List

from django.utils import timezone

from app import config
from custard_app.models import User, Company, Role, RoleType

from django.db import transaction
from django.db.models import Q, QuerySet
from django.conf import settings
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature

from custard_app.models import User, Company, Role, RoleType
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


def create_user(username: str, email: str, password: str, company: Company) -> User:
    """
    Create a new user.

    Parameters:
        username (str): The username of the user.
        email (str): The email of the user.
        password (str): The password of the user.
        company (Company): The company object.

    Returns:
        User: The created user object.
    """
    user = User()
    user.set_password(password)
    user.username = username
    user.email = email
    user.is_active = False
    user.company = company
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
        *, creator: User, company: Company, email: str, password: str, role_type: str
    ) -> User:
        """
        Create a new user for the company (one user per company).

        Parameters:
            creator (User): The admin user creating this user.
            company (Company): The company the user belongs to.
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
                "name": f"{company.name} {role_type}",
                "description": f"{role_type} role for {company.name}",
            },
        )

        # Create the user
        user = User.objects.create(
            email=email,
            username=email,
            company=company,
            role=role,
            is_active=True,
        )
        user.set_password(password)
        user.save()
        return user

    @staticmethod
    def get_company_users(*, user: User) -> QuerySet:
        """
        Get all users in the company (only one user per company in this scenario).

        Parameters:
            user (User): The user making the request.

        Returns:
            QuerySet: A queryset containing the single user for the company.
        """
        return User.objects.filter(company=user.company)

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
        if user.company != admin.company:
            raise PermissionDenied("Cannot modify users from different companies")

        # Update role if changed
        if user.role.role_type != role_type:
            role = Role.objects.get(role_type=role_type)
            user.role = role
            user.save()

        return user