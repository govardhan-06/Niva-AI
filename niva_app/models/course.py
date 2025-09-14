from niva_app.models.base import TimestampBase
from django.db.models import (
    CharField,
    TextField,
    IntegerField,
    BooleanField,
    DecimalField,
    Index,
)

class Course(TimestampBase):
    """
    Represents a Course/Exam type in the interview preparation system.
    
    This model stores comprehensive course information for different types of
    competitive exams and interview preparations like UPSC, SSB, etc.
    
    Fields:
        name (CharField): Course name
        description (TextField): Detailed description of the course
        is_active (BooleanField): Whether course is currently active
        passing_score (DecimalField): Minimum score required to pass
        max_score (DecimalField): Maximum possible score
        syllabus (TextField): Course syllabus and topics covered
        prerequisites (TextField): Prerequisites for the course
        instructions (TextField): Special instructions for candidates
        evaluation_criteria (TextField): How the interview will be evaluated
    """
    
    name = CharField(
        max_length=150,
        null=False,
        blank=False,
        help_text="Course name (e.g., UPSC Civil Services, SSB Interview)",
    )
    
    description = TextField(
        blank=True,
        help_text="Detailed description of the course and what it covers"
    )
    
    is_active = BooleanField(
        default=True,
        help_text="Whether this course is currently active and available"
    )
    
    passing_score = DecimalField(
        max_digits=5,
        decimal_places=2,
        default=60.00,
        help_text="Minimum score required to pass (out of max_score)"
    )
    
    max_score = DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00,
        help_text="Maximum possible score for this course"
    )
    
    syllabus = TextField(
        blank=True,
        help_text="Course syllabus and topics that will be covered in the interview"
    )
    
    instructions = TextField(
        blank=True,
        help_text="Special instructions for candidates taking this course"
    )
    
    evaluation_criteria = TextField(
        blank=True,
        help_text="Detailed criteria on how the interview will be evaluated"
    )

    def __str__(self):
        return f"{self.name}"

    def get_success_rate(self):
        """Calculate success rate based on students who passed"""
        from django.db.models import Avg
        feedbacks = self.students.prefetch_related('feedbacks').all()
        if not feedbacks:
            return 0
        
        passed_count = sum(1 for student in feedbacks 
                          if student.feedbacks.exists() and 
                          student.feedbacks.latest('created_at').overall_rating >= 6)
        return (passed_count / len(feedbacks)) * 100 if feedbacks else 0

    class Meta:
        ordering = ['-created_at']
        indexes = [
            Index(fields=['name']),
            Index(fields=['is_active']),
        ]