import logging
import uuid
from typing import Optional, Dict, Any, List, Tuple
from django.db import transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import QuerySet, Q, Avg, Count, Min, Max
from niva_app.models.feedback import Feedback
from niva_app.models.students import Student
from niva_app.models.agents import Agent
from niva_app.models.course import Course
from niva_app.models.dailycalls import DailyCall

logger = logging.getLogger(__name__)


def _safe_uuid_convert(id_string: str) -> Optional[str]:
    """Safely convert string to UUID format, return None if invalid"""
    try:
        # Try to convert to UUID to validate format
        uuid.UUID(id_string)
        return id_string
    except (ValueError, TypeError):
        logger.warning(f"Invalid UUID format: {id_string}")
        return None


def get_feedback(feedback_id: str) -> Optional[Feedback]:
    """
    Get a specific feedback by ID.

    Parameters:
        feedback_id (str): The UUID of the feedback to retrieve

    Returns:
        Feedback: The feedback object if found, else None
    """
    if not _safe_uuid_convert(feedback_id):
        return None
        
    try:
        return Feedback.objects.select_related(
            'student', 'agent', 'daily_call'
        ).get(id=feedback_id)
    except Feedback.DoesNotExist:
        logger.warning(f"Feedback with ID {feedback_id} not found")
        return None


def get_student_feedbacks(
    student_id: str, 
    course_id: str,
    limit: int = 10, 
    offset: int = 0
) -> Tuple[List[Feedback], int]:
    """
    Get all feedbacks for a specific student and course.

    Parameters:
        student_id (str): The UUID of the student
        course_id (str): The UUID of the course
        limit (int): Maximum number of feedbacks to return
        offset (int): Number of feedbacks to skip

    Returns:
        Tuple[List[Feedback], int]: List of feedbacks and total count
    """
    if not _safe_uuid_convert(student_id) or not _safe_uuid_convert(course_id):
        return [], 0
        
    try:
        student = Student.objects.get(id=student_id)
        course = Course.objects.get(id=course_id)
    except Student.DoesNotExist:
        logger.warning(f"Student with ID {student_id} not found")
        return [], 0
    except Course.DoesNotExist:
        logger.warning(f"Course with ID {course_id} not found")
        return [], 0

    # Check if student is enrolled in the course
    if not student.course.filter(id=course_id).exists():
        logger.warning(f"Student {student_id} is not enrolled in course {course_id}")
        return [], 0

    queryset = Feedback.objects.filter(
        student=student
    ).select_related(
        'student', 'agent', 'daily_call'
    ).order_by('-created_at')

    total_count = queryset.count()
    feedbacks = list(queryset[offset:offset + limit])
    
    logger.info(f"Retrieved {len(feedbacks)} feedbacks for student {student_id} in course {course_id}")
    return feedbacks, total_count


def get_feedbacks_by_user_id(
    user_id: str,
    course_id: Optional[str] = None,
    limit: int = 10,
    offset: int = 0
) -> Tuple[List[Feedback], int]:
    """
    Get all feedbacks for a user by user_id (user is mapped to student).

    Parameters:
        user_id (str): The UUID of the user
        course_id (str, optional): The UUID of the course to filter by
        limit (int): Maximum number of feedbacks to return
        offset (int): Number of feedbacks to skip

    Returns:
        Tuple[List[Feedback], int]: List of feedbacks and total count
    """
    if not _safe_uuid_convert(user_id):
        logger.warning(f"Invalid user_id format: {user_id}")
        return [], 0
    
    # Get student by user_id
    from niva_app.services.student import get_student_by_user_id
    student = get_student_by_user_id(user_id)
    
    if not student:
        logger.warning(f"No student profile found for user_id {user_id}")
        return [], 0
    
    # Build queryset
    queryset = Feedback.objects.filter(
        student=student
    ).select_related(
        'student', 'agent', 'daily_call'
    )
    
    # Filter by course if provided
    if course_id:
        if not _safe_uuid_convert(course_id):
            logger.warning(f"Invalid course_id format: {course_id}")
            return [], 0
        
        try:
            course = Course.objects.get(id=course_id)
            # Check if student is enrolled in the course
            if not student.course.filter(id=course_id).exists():
                logger.warning(f"Student {student.id} is not enrolled in course {course_id}")
                return [], 0
        except Course.DoesNotExist:
            logger.warning(f"Course with ID {course_id} not found")
            return [], 0
        
        queryset = queryset.filter(daily_call__course_id=course_id)
    
    # Order and paginate
    queryset = queryset.order_by('-created_at')
    total_count = queryset.count()
    feedbacks = list(queryset[offset:offset + limit])
    
    logger.info(f"Retrieved {len(feedbacks)} feedbacks for user_id {user_id} (student_id: {student.id})")
    return feedbacks, total_count

def get_all_feedbacks(
    student_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    course_id: Optional[str] = None,
    min_rating: Optional[int] = None,
    max_rating: Optional[int] = None,
    limit: int = 10,
    offset: int = 0,
    ordering: str = '-created_at'
) -> Tuple[List[Feedback], int, Dict[str, Any]]:
    """
    Get all feedbacks with optional filtering and statistics.

    Parameters:
        student_id (str, optional): Filter by student ID
        agent_id (str, optional): Filter by agent ID
        course_id (str, optional): Filter by course ID
        min_rating (int, optional): Minimum overall rating filter
        max_rating (int, optional): Maximum overall rating filter
        limit (int): Maximum number of feedbacks to return
        offset (int): Number of feedbacks to skip
        ordering (str): Ordering field (e.g., '-created_at', 'overall_rating')

    Returns:
        Tuple[List[Feedback], int, Dict]: List of feedbacks, total count, and statistics
    """
    queryset = Feedback.objects.select_related(
        'student', 'agent', 'daily_call'
    )

    # Apply filters
    if student_id:
        if not _safe_uuid_convert(student_id):
            return [], 0, {}
        try:
            Student.objects.get(id=student_id)
            queryset = queryset.filter(student_id=student_id)
        except Student.DoesNotExist:
            logger.warning(f"Student with ID {student_id} not found")
            return [], 0, {}

    if agent_id:
        if not _safe_uuid_convert(agent_id):
            return [], 0, {}
        try:
            Agent.objects.get(id=agent_id)
            queryset = queryset.filter(agent_id=agent_id)
        except Agent.DoesNotExist:
            logger.warning(f"Agent with ID {agent_id} not found")
            return [], 0, {}

    if course_id:
        if not _safe_uuid_convert(course_id):
            return [], 0, {}
        try:
            course = Course.objects.get(id=course_id)
            student_ids = course.students.values_list('id', flat=True)
            queryset = queryset.filter(student_id__in=student_ids)
        except Course.DoesNotExist:
            logger.warning(f"Course with ID {course_id} not found")
            return [], 0, {}

    if min_rating is not None:
        queryset = queryset.filter(overall_rating__gte=min_rating)

    if max_rating is not None:
        queryset = queryset.filter(overall_rating__lte=max_rating)

    # Apply ordering
    queryset = queryset.order_by(ordering)

    # Get statistics
    stats = {}
    if queryset.exists():
        stats = {
            'total_feedbacks': queryset.count(),
            'average_overall_rating': queryset.aggregate(
                avg=Avg('overall_rating')
            )['avg'] or 0,
            'average_communication_rating': queryset.aggregate(
                avg=Avg('communication_rating')
            )['avg'] or 0,
            'average_technical_rating': queryset.aggregate(
                avg=Avg('technical_rating')
            )['avg'] or 0,
            'average_confidence_rating': queryset.aggregate(
                avg=Avg('confidence_rating')
            )['avg'] or 0,
            'rating_distribution': dict(
                queryset.values('overall_rating').annotate(
                    count=Count('overall_rating')
                ).values_list('overall_rating', 'count')
            )
        }

    total_count = queryset.count()
    feedbacks = list(queryset[offset:offset + limit])
    
    logger.info(f"Retrieved {len(feedbacks)} feedbacks with filters applied")
    return feedbacks, total_count, stats


def get_feedback_statistics(
    student_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    course_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get comprehensive feedback statistics.

    Parameters:
        student_id (str, optional): Filter by student ID
        agent_id (str, optional): Filter by agent ID
        course_id (str, optional): Filter by course ID

    Returns:
        Dict[str, Any]: Statistics including averages, distributions, and trends
    """
    queryset = Feedback.objects.select_related('student', 'agent', 'daily_call')

    # Apply filters
    if student_id:
        if not _safe_uuid_convert(student_id):
            return {}
        queryset = queryset.filter(student_id=student_id)
    if agent_id:
        if not _safe_uuid_convert(agent_id):
            return {}
        queryset = queryset.filter(agent_id=agent_id)
    if course_id:
        if not _safe_uuid_convert(course_id):
            return {}
        try:
            course = Course.objects.get(id=course_id)
            student_ids = course.students.values_list('id', flat=True)
            queryset = queryset.filter(student_id__in=student_ids)
        except Course.DoesNotExist:
            logger.warning(f"Course with ID {course_id} not found")
            return {}

    if not queryset.exists():
        return {}

    # Calculate comprehensive statistics
    stats = queryset.aggregate(
        total_feedbacks=Count('id'),
        avg_overall=Avg('overall_rating'),
        avg_communication=Avg('communication_rating'),
        avg_technical=Avg('technical_rating'),
        avg_confidence=Avg('confidence_rating'),
        min_overall=Min('overall_rating'),
        max_overall=Max('overall_rating')
    )

    # Rating distribution
    rating_distribution = dict(
        queryset.values('overall_rating').annotate(
            count=Count('overall_rating')
        ).values_list('overall_rating', 'count')
    )

    # Performance categories
    excellent_count = queryset.filter(overall_rating__gte=8).count()
    good_count = queryset.filter(overall_rating__gte=6, overall_rating__lt=8).count()
    average_count = queryset.filter(overall_rating__gte=4, overall_rating__lt=6).count()
    poor_count = queryset.filter(overall_rating__lt=4).count()

    return {
        **stats,
        'rating_distribution': rating_distribution,
        'performance_categories': {
            'excellent': excellent_count,
            'good': good_count,
            'average': average_count,
            'poor': poor_count
        },
        'success_rate': (excellent_count + good_count) / stats['total_feedbacks'] * 100 if stats['total_feedbacks'] > 0 else 0
    }
