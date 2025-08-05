from django.db import models
from niva_app.models.base import TimestampBase

class Feedback(TimestampBase):
    """
    Feedback model for storing student interview feedback.
    
    This model stores feedback data after student interviews,
    including ratings, comments, and improvement suggestions.
    
    Fields:
        student (ForeignKey): Student who received the feedback
        daily_call (ForeignKey): Call session associated with this feedback
        agent (ForeignKey): Agent that conducted the interview
        overall_rating (IntegerField): Overall performance rating (1-10)
        communication_rating (IntegerField): Communication skills rating (1-10)
        technical_rating (IntegerField): Technical knowledge rating (1-10)
        confidence_rating (IntegerField): Confidence level rating (1-10)
        feedback_text (TextField): Detailed feedback comments
        strengths (TextField): Areas where student performed well
        improvements (TextField): Areas that need improvement
        recommendations (TextField): Specific recommendations for growth
    """
    
    student = models.ForeignKey(
        'niva_app.Student',
        on_delete=models.CASCADE,
        related_name='feedbacks',
        help_text="Student who received the feedback"
    )
    
    daily_call = models.OneToOneField(
        'niva_app.DailyCall',
        on_delete=models.CASCADE,
        related_name='feedback',
        help_text="Call session associated with this feedback"
    )
    
    agent = models.ForeignKey(
        'niva_app.Agent',
        on_delete=models.CASCADE,
        related_name='feedbacks',
        help_text="Agent that conducted the interview"
    )
    
    # Rating fields (1-10 scale)
    overall_rating = models.IntegerField(
        choices=[(i, i) for i in range(1, 11)],
        help_text="Overall performance rating (1-10)"
    )
    
    communication_rating = models.IntegerField(
        choices=[(i, i) for i in range(1, 11)],
        help_text="Communication skills rating (1-10)"
    )
    
    technical_rating = models.IntegerField(
        choices=[(i, i) for i in range(1, 11)],
        help_text="Technical knowledge rating (1-10)"
    )
    
    confidence_rating = models.IntegerField(
        choices=[(i, i) for i in range(1, 11)],
        help_text="Confidence level rating (1-10)"
    )
    
    # Text feedback fields
    feedback_text = models.TextField(
        help_text="Detailed feedback comments"
    )
    
    strengths = models.TextField(
        blank=True,
        help_text="Areas where student performed well"
    )
    
    improvements = models.TextField(
        blank=True,
        help_text="Areas that need improvement"
    )
    
    recommendations = models.TextField(
        blank=True,
        help_text="Specific recommendations for growth"
    )

    def __str__(self):
        return f"Feedback for {self.student.first_name} {self.student.last_name} - Rating: {self.overall_rating}/10"

    def get_average_rating(self):
        """Calculate average rating across all categories"""
        return (self.overall_rating + self.communication_rating + 
                self.technical_rating + self.confidence_rating) / 4

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['overall_rating']),
            models.Index(fields=['created_at']),
        ]