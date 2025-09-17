import logging
from typing import Optional, List
from django.db import transaction
from niva_app.models import Agent, Course

logger = logging.getLogger(__name__)


def create_agent_for_course(course: Course) -> Agent:
    """
    Create a default agent for a course.
    
    Parameters:
        course (Course): The course to create an agent for
        
    Returns:
        Agent: The created agent object
    """
    # agent_name = f"{course.name} Assistant"
    agent_name = "Priya"
    
    # Create a default agent for the course
    agent = Agent.objects.create(
        name=agent_name,
        is_active=True,
        language=course.language, 
        agent_type='Course Assistant'
    )
    
    # Associate the agent with the course
    agent.courses.add(course)
    
    logger.info(f"Created agent '{agent_name}' for course '{course.name}'")
    return agent


def get_agents_for_course(course_id: str) -> List[Agent]:
    """
    Get all agents associated with a course.
    
    Parameters:
        course_id (str): Course ID
        
    Returns:
        List[Agent]: List of agents associated with the course
    """
    try:
        course = Course.objects.get(id=course_id)
        return list(course.agents.all())
    except Course.DoesNotExist:
        return []


def update_agent(
    agent_id: str,
    name: str = None,
    language: str = None,
    agent_type: str = None,
    is_active: bool = None
) -> Optional[Agent]:
    """
    Update an agent.
    
    Parameters:
        agent_id (str): Agent ID
        name (str): Agent name (optional)
        language (str): Agent language (optional)
        agent_type (str): Agent type (optional)
        is_active (bool): Whether agent is active (optional)
        
    Returns:
        Agent: Updated agent object if found, None otherwise
    """
    try:
        agent = Agent.objects.get(id=agent_id)
        
        update_fields = []
        
        if name is not None:
            agent.name = name
            update_fields.append('name')
        if language is not None:
            agent.language = language
            update_fields.append('language')
        if agent_type is not None:
            agent.agent_type = agent_type
            update_fields.append('agent_type')
        if is_active is not None:
            agent.is_active = is_active
            update_fields.append('is_active')
            
        if update_fields:
            update_fields.append('updated_at')
            agent.save(update_fields=update_fields)
            logger.info(f"Updated agent: {agent.name}")
            
        return agent
        
    except Agent.DoesNotExist:
        return None