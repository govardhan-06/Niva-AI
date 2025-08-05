from django.db.models import(
    CharField, ForeignKey, TextField, Index, CASCADE, UUIDField
)
from niva_app.models.base import TimestampBase

class DailyRooms(TimestampBase):
    """
    Stores information about Daily.co rooms.
    
    This model tracks Daily.co room configurations, including room details,
    SIP endpoints, and authentication tokens.
    
    Fields:
        course (ForeignKey): course associated with this room
        agent (ForeignKey): Agent associated with this room
        daily_room_id (UUIDField): UUID of the Daily.co room
        daily_call_id (ForeignKey): Foreign key to the DailyCall model
        daily_room_url (CharField): URL of the Daily.co room
        daily_room_name (CharField): Name of the Daily.co room
        daily_sip_endpoint (CharField): SIP endpoint for the call
        daily_room_token (TextField): JWT token for accessing the Daily.co room
    
    Relationships:
        - Related to course (many-to-one)
        - Related to Agent (many-to-one)
        - Related to DailyCall (many-to-one)
    """
    
    course = ForeignKey(
        'niva_app.Course',  
        on_delete=CASCADE,
        related_name='daily_rooms',
        help_text="Course associated with this room"
    )
    
    agent = ForeignKey(
        'niva_app.Agent',
        on_delete=CASCADE,
        related_name='daily_rooms',
        help_text="Agent associated with this room"
    )
    
    daily_room_id = UUIDField(
        unique=True,
        help_text="UUID of the Daily.co room"
    )
    
    daily_call_id = ForeignKey(
        'niva_app.DailyCall',
        on_delete=CASCADE,
        related_name='daily_rooms',
        help_text="Foreign key to the DailyCall model"
    )
    
    daily_room_url = CharField(
        max_length=255,
        help_text="URL of the Daily.co room"
    )
    
    daily_room_name = CharField(
        max_length=100,
        help_text="Name of the Daily.co room"
    )
    
    daily_sip_endpoint = CharField(
        max_length=255,
        help_text="SIP endpoint for the call"
    )
    
    daily_room_token = TextField(
        help_text="JWT token for accessing the Daily.co room"
    )

    def __str__(self):
        return f"Room {self.daily_room_name} - {self.course.name}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            Index(fields=['daily_room_id']),
            Index(fields=['daily_room_name']),
            Index(fields=['created_at']),
        ]
        verbose_name = "Daily Room"
        verbose_name_plural = "Daily Rooms"