from niva_app.models.base import TimestampBase
from django.db import models
from django.conf import settings

class Student(TimestampBase):
    """
    Represents a Student in the system.
    
    This model stores personal information about Students and their
    relationships with course, call records, score, etc.
    
    Fields:
        user (OneToOneField): Associated user account (optional)
        first_name (TextField): Student's first name
        last_name (TextField): Student's last name
        gender (TextField): Student's gender
        date_of_birth (DateField): Student's date of birth
        email (EmailField): Student's email address
        phone_number (CharField): Student's phone number
        course (ManyToManyField): course associated with this Student
    
    Relationships:
        - Related to User (one-to-one, optional)
        - Related to course (many-to-many)
        - Related to DailyCall (one-to-many)
    """
    
    Genders = [
        ("MALE", "male"),
        ("FEMALE", "female"),
        ("RATHER_NOT_SAY", "rather not say"),
        ("UNKNOWN", "unknown"),
    ]
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_profile',
        help_text="Associated user account (if the student has an account)"
    )
    first_name = models.TextField(null=False, blank=False)
    last_name = models.TextField(null=False, blank=True)
    gender = models.TextField(choices=Genders, null=False, default="UNKNOWN")
    date_of_birth = models.DateField(blank=True, null=True)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20, blank=False, null=False)   

    course = models.ManyToManyField(
        'niva_app.Course',  
        related_name='students',  
        help_text="Course associated with this Student"
    )

    def save(self, *args, **kwargs):
        self.phone_number = self.phone_number.strip()
        if not self.phone_number.startswith("+"):
            self.phone_number = f"+{self.phone_number}"
        super(Student, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['email']),
        ]