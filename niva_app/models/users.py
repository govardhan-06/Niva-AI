from django.contrib.auth.models import AbstractUser, Permission
from django.db.models import (
    Model,
    CharField,
    EmailField,
    BooleanField,
    ForeignKey,
    ManyToManyField,
    TextChoices,
    SET_NULL,
    CASCADE,
    QuerySet
)
from phonenumber_field.modelfields import PhoneNumberField
from niva_app.models.base import TimestampBase

class RoleType(TextChoices):
    ADMIN = "admin", "Admin"
    USER = "user", "User"

class UserStatus(TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"
    BLOCKED = "blocked", "Blocked"

class Role(Model):
    name = CharField(
        max_length=100, unique=True, help_text="Unique role name for the user account"
    )
    description = CharField(max_length=255, help_text="Role description")
    permissions = ManyToManyField(Permission, help_text="Permissions for the role")
    role_type = CharField(
        max_length=20,
        choices=RoleType.choices,
        null=True,
        blank=True,
        help_text="Type of role"
    )

    def __str__(self):
        return f"{self.name} ({self.role_type})"

class User(AbstractUser, TimestampBase):
    email = EmailField(
        unique=True,
        help_text="Email address, This will be used for login"
    )
    is_email_verified = BooleanField(
        default=False, help_text="Email verification status"
    )

    phone_number = PhoneNumberField(
        null=True,
        blank=True,
        default=None,
        help_text="The phone number in E.164 format",
    )

    role = ForeignKey(
        Role, 
        on_delete=SET_NULL, 
        null=True, 
        help_text="Role for the user account"
    )

    class Meta:
        permissions = [
            ("can_view_user", "Can view all users"),
            ("can_manage_user", "Can manage users"),
        ]

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        super(User, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} - {self.email}"

    def is_admin(self):
        return bool(self.role and self.role.role_type == RoleType.ADMIN)