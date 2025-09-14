import logging
from typing import Optional, Dict, Any, List
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from niva_app.models.course import Course

logger = logging.getLogger(__name__)


@transaction.atomic
def create_course(
    name: str,
    description: str = "",
    is_active: bool = True,
    passing_score: float = 60.00,
    max_score: float = 100.00,
    syllabus: str = "",
    instructions: str = "",
    evaluation_criteria: str = ""
) -> Course:
    """
    Create a new course and its associated agent.

    Parameters:
        name (str): Course name
        description (str): Course description
        is_active (bool): Whether course is active
        passing_score (float): Minimum passing score
        max_score (float): Maximum possible score
        syllabus (str): Course syllabus
        instructions (str): Course instructions
        evaluation_criteria (str): Evaluation criteria

    Returns:
        Course: The created course object with associated agent
    """
    # Create the course
    course = Course.objects.create(
        name=name,
        description=description,
        is_active=is_active,
        passing_score=passing_score,
        max_score=max_score,
        syllabus=syllabus,
        instructions=instructions,
        evaluation_criteria=evaluation_criteria
    )
    logger.info(f"Created course: {course.name}")
    
    # Import here to avoid circular imports
    from niva_app.services.agent import create_agent_for_course
    
    # Create associated agent
    agent = create_agent_for_course(course)
    logger.info(f"Created associated agent: {agent.name} for course: {course.name}")
    
    return course


def get_course(course_id: str) -> Optional[Course]:
    """
    Get a course by ID.

    Parameters:
        course_id (str): Course ID

    Returns:
        Course: Course object if found, None otherwise
    """
    try:
        return Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return None


def get_all_courses(is_active: bool = None) -> QuerySet[Course]:
    """
    Get all courses.

    Parameters:
        is_active (bool): Filter by active status (optional)

    Returns:
        QuerySet: Queryset of courses
    """
    queryset = Course.objects.all()
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)
    return queryset.order_by('-created_at')


def update_course(
    course_id: str,
    name: str = None,
    description: str = None,
    is_active: bool = None,
    passing_score: float = None,
    max_score: float = None,
    syllabus: str = None,
    instructions: str = None,
    evaluation_criteria: str = None
) -> Optional[Course]:
    """
    Update a course.

    Parameters:
        course_id (str): Course ID
        name (str): Course name (optional)
        description (str): Course description (optional)
        is_active (bool): Whether course is active (optional)
        passing_score (float): Minimum passing score (optional)
        max_score (float): Maximum possible score (optional)
        syllabus (str): Course syllabus (optional)
        instructions (str): Course instructions (optional)
        evaluation_criteria (str): Evaluation criteria (optional)

    Returns:
        Course: Updated course object if found, None otherwise
    """
    course = get_course(course_id)
    if not course:
        return None

    update_fields = []
    
    if name is not None:
        course.name = name
        update_fields.append('name')
        
        # Update associated agent name as well
        try:
            from niva_app.services.agent import update_agent
            agents = course.agents.all()
            for agent in agents:
                update_agent(str(agent.id), name=f"{name} Assistant")
        except Exception as e:
            logger.warning(f"Failed to update agent name: {e}")
            
    if description is not None:
        course.description = description
        update_fields.append('description')
    if is_active is not None:
        course.is_active = is_active
        update_fields.append('is_active')
        
        # Update associated agents' active status
        try:
            from niva_app.services.agent import update_agent
            agents = course.agents.all()
            for agent in agents:
                update_agent(str(agent.id), is_active=is_active)
        except Exception as e:
            logger.warning(f"Failed to update agent status: {e}")
            
    if passing_score is not None:
        course.passing_score = passing_score
        update_fields.append('passing_score')
    if max_score is not None:
        course.max_score = max_score
        update_fields.append('max_score')
    if syllabus is not None:
        course.syllabus = syllabus
        update_fields.append('syllabus')
    if instructions is not None:
        course.instructions = instructions
        update_fields.append('instructions')
    if evaluation_criteria is not None:
        course.evaluation_criteria = evaluation_criteria
        update_fields.append('evaluation_criteria')

    if update_fields:
        update_fields.append('updated_at')
        course.save(update_fields=update_fields)
        logger.info(f"Updated course: {course.name}")

    return course


def delete_course(course_id: str) -> bool:
    """
    Delete a course and its associated agents.

    Parameters:
        course_id (str): Course ID

    Returns:
        bool: True if deleted, False if not found
    """
    course = get_course(course_id)
    if not course:
        return False

    course_name = course.name
    
    # Delete associated agents first
    agents = course.agents.all()
    for agent in agents:
        agent.delete()
        logger.info(f"Deleted associated agent: {agent.name}")
    
    # Delete the course
    course.delete()
    logger.info(f"Deleted course: {course_name}")
    return True


def validate_course_data(data: Dict[str, Any]) -> None:
    """
    Validate course data.

    Parameters:
        data (dict): Course data to validate

    Raises:
        ValidationError: If validation fails
    """
    errors = {}

    if 'name' in data and not data['name'].strip():
        errors['name'] = ['Course name is required']

    if 'passing_score' in data and 'max_score' in data:
        if data['passing_score'] > data['max_score']:
            errors['passing_score'] = ['Passing score cannot be greater than max score']

    if 'passing_score' in data and data['passing_score'] < 0:
        errors['passing_score'] = ['Passing score cannot be negative']

    if 'max_score' in data and data['max_score'] <= 0:
        errors['max_score'] = ['Max score must be greater than 0']

    if errors:
        raise ValidationError(errors)