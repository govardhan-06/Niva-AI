from django.forms import CharField
from niva_app.lib.validators import agent_name_validator
from niva_app.models.base import TimestampBase
from django.db.models import (
    TextField,
    BooleanField,
    CharField,
    ForeignKey,
    ManyToManyField,
    CASCADE,
    Index
)

class Agent(TimestampBase):
    """
    Represents an AI agent with specific behaviors and configurations.
    
    This model defines the properties and behaviors of an AI agent,
    including its prompts, role definitions, and status flags.
    
    Fields:
        name (CharField): Name of the agent
        courses (ManyToManyField): Courses this agent can handle
        is_active (Boolean): Agent's active status
        language (CharField): The language the agent communicates in
        agent_type (TextField): Type of agent (e.g., 'HR', 'Technical')
    """
    
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('hi', 'Hindi'),
        ('ml', 'Malayalam'),
        ('ta', 'Tamil'),
    ]
    
    name = CharField(
        blank=True,
        max_length=255,
        validators=[agent_name_validator],
        help_text="Name of the agent"
    )

    courses = ManyToManyField(
        'niva_app.Course',
        related_name="agents",
        help_text="Courses this agent can handle",
    )

    is_active = BooleanField(
        default=True,
        help_text="Agent status. This can be used to mark agent as active or inactive without deleting it.",
    )

    language = CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default='en',
        help_text="The language the agent communicates in (default language)"
    )
    
    agent_type = TextField(
        blank=True,
        help_text="Type of agent (e.g., 'HR', 'Technical')"
    )

    def __str__(self):
        course_names = ", ".join([course.name for course in self.courses.all()[:2]])
        return f"{self.name} - {course_names}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            Index(fields=['is_active']),
            Index(fields=['language']),
        ]