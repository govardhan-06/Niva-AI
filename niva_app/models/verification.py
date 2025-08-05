import uuid
from django.db import models
from django.db.models import (
    CharField,
    DateTimeField,
    ForeignKey,
    EmailField,
    CASCADE
)
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
from niva_app.models.base import TimestampBase

class EmailVerificationOTP(TimestampBase):
    email = EmailField(unique=True)
    otp = CharField(max_length=6)

    def __str__(self):
        return self.email

    def is_otp_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(minutes=10)

class PhoneVerificationOTP(TimestampBase):
    # Remove company reference since no company model needed
    phone_number = PhoneNumberField(
        help_text="Phone number to be verified"
    )

    otp = CharField(max_length=6)

    def __str__(self):
        return f"{self.phone_number}"

    def is_otp_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(minutes=10)

    class Meta:
        # Remove unique_together constraint that included company
        pass