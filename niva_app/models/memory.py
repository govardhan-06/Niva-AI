from niva_app.models.base import TimestampBase
from django.db import models
from django.db.models import CASCADE

class MemoryType(models.TextChoices):
    DOCUMENT = "document", "Document"

class Memory(TimestampBase):
    """
    Represents a memory or knowledge source for courses and agents.
    
    This model stores information about different types of memory sources
    that agents can use for specific courses, such as documents
    
    Fields:
        course (ForeignKey): Course associated with this memory
        agent (ForeignKey): Specific agent this memory is for
        name (CharField): Name of the memory source
        type (CharField): Type of memory
        url (URLField): URL or location of the memory source
        doc_ids (JSONField): Document IDs associated with this memory
        content_summary (TextField): Summary of the content
        is_active (BooleanField): Whether this memory is active
    """
    
    course = models.ForeignKey(
        'niva_app.Course',
        on_delete=CASCADE,
        related_name="memories",
        help_text="Course associated with this memory"
    )
    
    agent = models.ForeignKey(
        'niva_app.Agent',
        on_delete=CASCADE,
        related_name="memories",
        null=True,
        blank=True,
        help_text="Specific agent this memory is for"
    )
    
    name = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        help_text="Name of the memory source"
    )
    
    type = models.CharField(
        choices=MemoryType.choices,
        max_length=50,
        help_text="Type of memory (document, course material, etc.)"
    )
    
    url = models.URLField(
        help_text="URL or location of the memory source"
    )
    
    doc_ids = models.JSONField(
        blank=True,
        null=True,
        help_text="Document IDs associated with this memory"
    )
    
    content_summary = models.TextField(
        blank=True,
        help_text="Brief summary of what this memory contains"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this memory source is currently active"
    )

    def __str__(self):
        return f"{self.name} ({self.type}) - {self.course.name}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['course']),
            models.Index(fields=['agent']),
            models.Index(fields=['type']),
            models.Index(fields=['is_active']),
        ]
        verbose_name_plural = "Memories"