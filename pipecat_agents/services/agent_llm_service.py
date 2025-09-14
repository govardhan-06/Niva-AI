import logging
import os
from pipecat_agents.services.agent_context import AgentContextService

from pipecat_agents.services.inbound_flow_service import (
    interview_started,
    academic_background_collected,
    program_interest_discussed,
    experience_reviewed,
    behavioral_assessment_completed,
    student_questions_addressed,
    save_interview_data
)
from pipecat.services.deepgram.stt import DeepgramSTTService
from deepgram import LiveOptions
from pipecat.services.aws import AWSPollyTTSService
from pipecat.transcriptions.language import Language

from app import config

logger = logging.getLogger(__name__)

def get_inbound_tools_description():
    """Get description of available tools for student interview agents."""
    return """
AVAILABLE TOOLS - Use these to conduct effective student interviews:

INTERVIEW INITIATION:
• interview_started(student_name, email, phone, program_interest): Start interview and collect basic student information

ACADEMIC ASSESSMENT:
• academic_background_collected(current_education_level, institution, gpa, graduation_year, major): Collect academic background information

PROGRAM EVALUATION:
• program_interest_discussed(program_choice, motivation, career_goals): Assess student's program interest and motivation

EXPERIENCE REVIEW:
• experience_reviewed(work_experience, projects, skills, achievements): Evaluate student's experience and skills

BEHAVIORAL ASSESSMENT:
• behavioral_assessment_completed(scenario_response, problem_solving_approach, teamwork_example): Conduct behavioral interviews

STUDENT ENGAGEMENT:
• student_questions_addressed(questions_asked, questions_answered): Handle student's questions about the program

DATA MANAGEMENT:
• save_interview_data(overall_impression, strengths, areas_for_improvement, recommendation): Save complete interview assessment

IMPORTANT: Use these functions to conduct thorough interviews, assess candidates fairly, and maintain detailed records of the interview process.
"""

def inbound_handlers_register(llm):
    """
    Register handlers for student interview flow.
    """
    logger.info("Registering function handlers for student interview flow")
    
    # Interview initiation handlers
    llm.register_function("interview_started", interview_started)
    
    # Academic background handlers
    llm.register_function("academic_background_collected", academic_background_collected)
    
    # Program interest handlers
    llm.register_function("program_interest_discussed", program_interest_discussed)
    
    # Experience review handlers
    llm.register_function("experience_reviewed", experience_reviewed)
    
    # Behavioral assessment handlers
    llm.register_function("behavioral_assessment_completed", behavioral_assessment_completed)
    
    # Student questions handlers
    llm.register_function("student_questions_addressed", student_questions_addressed)
    
    # Data saving handlers
    llm.register_function("save_interview_data", save_interview_data)
    
    logger.info("All student interview function handlers registered successfully")

async def get_inbound_agent_context(course_id: str, agent_id: str) -> str:
    """
    Returns the dynamic context for interview agents.
    
    Args:
        course_id: ID of the course (using course_id parameter for compatibility)
        agent_id: ID of the agent
        
    Returns:
        str: System instruction/context for the interview agent
    """
    logger.info(f"PipecatAgentRunner: Getting interview agent context for agent_id: {agent_id}, course_id: {course_id}")
    
    try:
        # Validate the relationship first (using course instead of company for interviews)
        logger.info("Validating agent-course relationship...")
        is_valid = await AgentContextService.validate_agent_course_relationship(course_id, agent_id)
        if not is_valid:
            logger.error(f"Invalid agent-course relationship: agent {agent_id}, course {course_id}")
            raise ValueError("Invalid agent-course relationship")
        
        logger.info("Agent-course relationship validated successfully")
        
        # Get dynamic context for interview preparation
        logger.info("Fetching dynamic interview context...")
        context = await AgentContextService.get_agent_context(course_id, agent_id)
        
        # Add interview tools description
        # tools_description = get_inbound_tools_description()
        # full_context = f"{context}\n\n{tools_description}"
        full_context = context
        
        logger.info(f"Successfully loaded interview context for agent {agent_id}")
        return full_context
        
    except Exception as e:
        logger.error(f"Failed to get interview agent context: {e}")
        logger.exception("Full traceback:")
        
        # Fallback to a basic interview context with tools
        tools_description = get_inbound_tools_description()
        fallback_context = f"""
        You are a professional interview agent conducting student interviews for academic program admissions.
        You're trained to assess candidates fairly, evaluate their knowledge and skills, and provide a supportive interview experience.
        Your responses will be read aloud, so keep them natural and conversational.
        Be professional, encouraging, and focused on helping students showcase their abilities.
        Always maintain a fair and objective evaluation approach.
        
        {tools_description}
        """.strip()
        
        logger.warning(f"Using fallback interview context with tools")
        return fallback_context

def get_language_config(agent_language: str):
    """
    Get language-specific configuration for Deepgram STT, AWS Polly TTS, and LLM services
    """
    language_map = {
        'en': {
            'stt_language': Language.EN_US,
            'tts_language': Language.EN,
            'tts_voice_id': 'Joanna',  # AWS Polly voice
            'llm_language': 'en'
        },
        'hi': {
            'stt_language': Language.HI_IN,
            'tts_language': Language.HI,
            'tts_voice_id': 'Aditi',  # AWS Polly Hindi voice
            'llm_language': 'hi'
        },
    }
    
    return language_map.get(agent_language, language_map['en'])

async def configure_language_services(agent_id: str):
    """
    Configure Deepgram STT and AWS Polly TTS services based on agent's language
    """
    try:
        # Get agent's language
        agent_language = await AgentContextService.get_default_lang(agent_id)
        lang_config = get_language_config(agent_language)
        
        logger.info(f"Configuring services for language: {agent_language}")
        
        # Configure Deepgram STT
        stt = DeepgramSTTService(
            api_key=config.DEEPGRAM_STT_KEY,
            live_options=LiveOptions(
                model="nova-2",
                language=lang_config['stt_language'],
                interim_results=True,
                smart_format=True,
                punctuate=True,
                profanity_filter=True,
                vad_events=False, 
            )
        )
        
        # Configure AWS Polly TTS
        tts = AWSPollyTTSService(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            api_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region=os.getenv("AWS_REGION", "us-east-1"),
            voice_id=lang_config['tts_voice_id'],
            params=AWSPollyTTSService.InputParams(
                language=lang_config['tts_language'],
                engine="neural" 
            )
        )
        
        return stt, tts
        
    except Exception as e:
        logger.error(f"Error configuring language services: {e}")
        raise ValueError(f"Failed to configure language services: {str(e)}")