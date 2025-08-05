from django.utils import timezone
from uuid import uuid4
from django.db.models import UUIDField, DateTimeField, Model

class TimestampBase(Model):
    """
    Base model for all models with timestamp fields

    This model contains common fields that are used in multiple models. It provides the following fields:

    Attributes:
        - id (UUIDField): The unique identifier for the model
        - created_at (DateTimeField): The date and time the model was created
        - updated_at (DateTimeField): The date and time the model was last updated

    Meta:
        abstract = True # This model is abstract and should not be used directly
        ordering = ("-created_at",) # Order the models by created_at field in descending order
    """
    id = UUIDField(default=uuid4, editable=False, primary_key=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        # self.updated_at = timezone.now()
        super(TimestampBase, self).save(*args, **kwargs)
