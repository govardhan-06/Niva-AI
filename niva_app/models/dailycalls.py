from django.db.models import(
    CharField, ForeignKey, BooleanField, TextField, JSONField, Index, CASCADE, UUIDField
)
from niva_app.models.base import TimestampBase

class DailyCall(TimestampBase):
    """
    Stores information about Daily.co calls.
    
    This model tracks all calls made through the Daily.co system, including
    room information, call details, and associated metadata.
    
    Fields:
        call_sid (CharField): Unique identifier for the call
        call_summary (TextField): Summary of the call conversation
        student (ForeignKey): student associated with this call
        course (ForeignKey): course associated with this call
        agent (ForeignKey): Agent associated with this calll
    
    Relationships:
        - Related to course (many-to-one)
        - Related to student (many-to-one)
        - Related to Agent (many-to-one)
    """
    
    course = ForeignKey(
        'niva_app.Course', 
        on_delete=CASCADE,
        related_name='daily_calls',
        help_text="Course associated with this call"
    )
    
    call_sid = CharField(
        max_length=50,
        unique=False,
        help_text="Unique identifier for the call"
    )
    
    call_summary = TextField(
        blank=True,
        help_text="Summary of the call conversation"
    )

    transcription = TextField(
        blank=True,
        help_text="Transcription of the call conversation"
    )
    
    student = ForeignKey(
        'niva_app.Student',  
        on_delete=CASCADE,
        related_name='daily_calls',
        null=True,
        blank=True,
        help_text="Student associated with this call"
    )
    
    agent = ForeignKey(
        'niva_app.Agent',
        on_delete=CASCADE,
        related_name='daily_calls',
        help_text="Agent associated with this call"
    )

    def __str__(self):
        return f"Call {self.call_sid} - {self.student.first_name} {self.student.last_name}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            Index(fields=['call_sid']),
            Index(fields=['created_at']),
        ]