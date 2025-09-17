import logging
from typing import Optional, Dict, Any, List
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from niva_app.models.students import Student
from niva_app.models.course import Course

logger = logging.getLogger(__name__)


@transaction.atomic
def create_student(
    first_name: str,
    phone_number: str,
    last_name: str = "",
    gender: str = "UNKNOWN",
    date_of_birth: Optional[str] = None,
    email: str = "",
    course_ids: Optional[List[str]] = None
) -> Student:
    """
    Create a new student.

    Parameters:
        first_name (str): Student's first name
        phone_number (str): Student's phone number
        last_name (str): Student's last name (optional)
        gender (str): Student's gender (default: 'UNKNOWN')
        date_of_birth (str): Student's date of birth (optional)
        email (str): Student's email (optional)
        course_ids (List[str]): List of course IDs to associate with student

    Returns:
        Student: The created student object
    """
    # Clean and format phone number
    phone_number = phone_number.strip()
    if not phone_number.startswith("+"):
        phone_number = f"+{phone_number}"

    # Check if student already exists by phone number
    existing_student = Student.objects.filter(phone_number=phone_number).first()
    if existing_student:
        raise ValidationError(f"Student with phone number {phone_number} already exists")

    # Create the student
    student = Student.objects.create(
        first_name=first_name,
        last_name=last_name,
        gender=gender,
        date_of_birth=date_of_birth,
        email=email,
        phone_number=phone_number
    )

    # Associate with courses if provided
    if course_ids:
        courses = Course.objects.filter(id__in=course_ids)
        student.course.set(courses)
        logger.info(f"Associated student {student.phone_number} with {courses.count()} courses")

    logger.info(f"Created student: {student.first_name} {student.last_name} ({student.phone_number})")
    return student


def get_student(student_id: str) -> Optional[Student]:
    """
    Get a student by ID.

    Parameters:
        student_id (str): Student ID

    Returns:
        Optional[Student]: Student object if found, None otherwise
    """
    try:
        return Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return None


def get_all_students(
    course_id: Optional[str] = None,
    phone_number: Optional[str] = None,
    email: Optional[str] = None
) -> QuerySet:
    """
    Get all students with optional filtering.

    Parameters:
        course_id (str): Filter by course ID (optional)
        phone_number (str): Filter by phone number (optional)
        email (str): Filter by email (optional)

    Returns:
        QuerySet: Filtered students queryset
    """
    queryset = Student.objects.all()

    if course_id:
        queryset = queryset.filter(course__id=course_id)

    if phone_number:
        # Clean phone number
        phone_number = phone_number.strip()
        if not phone_number.startswith("+"):
            phone_number = f"+{phone_number}"
        queryset = queryset.filter(phone_number=phone_number)

    if email:
        queryset = queryset.filter(email__iexact=email)

    return queryset.distinct()


@transaction.atomic
def update_student(
    student_id: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    gender: Optional[str] = None,
    date_of_birth: Optional[str] = None,
    email: Optional[str] = None,
    phone_number: Optional[str] = None,
    course_ids: Optional[List[str]] = None
) -> Optional[Student]:
    """
    Update an existing student.

    Parameters:
        student_id (str): Student ID
        first_name (str): Student's first name (optional)
        last_name (str): Student's last name (optional)
        gender (str): Student's gender (optional)
        date_of_birth (str): Student's date of birth (optional)
        email (str): Student's email (optional)
        phone_number (str): Student's phone number (optional)
        course_ids (List[str]): List of course IDs to associate with student (optional)

    Returns:
        Optional[Student]: Updated student object if found, None otherwise
    """
    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return None

    # Update fields if provided
    if first_name is not None:
        student.first_name = first_name

    if last_name is not None:
        student.last_name = last_name

    if gender is not None:
        student.gender = gender

    if date_of_birth is not None:
        student.date_of_birth = date_of_birth

    if email is not None:
        student.email = email

    if phone_number is not None:
        # Clean and format phone number
        phone_number = phone_number.strip()
        if not phone_number.startswith("+"):
            phone_number = f"+{phone_number}"
        
        # Check if phone number is already taken by another student
        existing_student = Student.objects.filter(phone_number=phone_number).exclude(id=student_id).first()
        if existing_student:
            raise ValidationError(f"Phone number {phone_number} is already taken by another student")
        
        student.phone_number = phone_number

    # Update course associations if provided
    if course_ids is not None:
        courses = Course.objects.filter(id__in=course_ids)
        student.course.set(courses)
        logger.info(f"Updated course associations for student {student.phone_number}")

    student.save()
    logger.info(f"Updated student: {student.first_name} {student.last_name} ({student.phone_number})")
    return student


@transaction.atomic
def delete_student(student_id: str) -> bool:
    """
    Delete a student.

    Parameters:
        student_id (str): Student ID

    Returns:
        bool: True if deleted, False if not found
    """
    try:
        student = Student.objects.get(id=student_id)
        student.delete()
        logger.info(f"Deleted student: {student.first_name} {student.last_name} ({student.phone_number})")
        return True
    except Student.DoesNotExist:
        return False


def validate_student_data(data: Dict[str, Any]) -> None:
    """
    Validate student data.

    Parameters:
        data (Dict[str, Any]): Student data to validate

    Raises:
        ValidationError: If validation fails
    """
    # Validate phone number format
    phone_number = data.get("phone_number", "").strip()
    if not phone_number:
        raise ValidationError("Phone number is required")
    
    # Check for duplicate phone number (excluding current student if updating)
    student_id = data.get("student_id")
    existing_student = Student.objects.filter(phone_number=phone_number)
    if student_id:
        existing_student = existing_student.exclude(id=student_id)
    
    if existing_student.exists():
        raise ValidationError(f"Student with phone number {phone_number} already exists")

    # Validate email format if provided
    email = data.get("email", "").strip()
    if email:
        # Basic email validation is handled by the serializer
        pass

    # Validate course IDs if provided
    course_ids = data.get("course_ids", [])
    if course_ids:
        existing_courses = Course.objects.filter(id__in=course_ids)
        if existing_courses.count() != len(course_ids):
            raise ValidationError("One or more course IDs are invalid")
