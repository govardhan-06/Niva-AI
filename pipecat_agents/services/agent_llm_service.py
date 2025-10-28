import logging
import os
from pipecat_agents.services.agent_context import AgentContextService

from pipecat_agents.services.inbound_flow_service import (
    interview_progress_tracked,
    interview_completed
)
from pipecat.services.deepgram.stt import DeepgramSTTService
from deepgram import LiveOptions
# from pipecat.services.aws import AWSPollyTTSService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.transcriptions.language import Language

from app import config

logger = logging.getLogger(__name__)

def get_inbound_tools_description():
    """Get description of available tools for natural interview conversations."""
    return """
AVAILABLE TOOLS - Use these naturally during conversation:

CONVERSATION TRACKING:
• interview_progress_tracked(topic_discussed, response_quality, notes, student_name): 
  - Use when you want to note something interesting about the student's response
  - Track key topics as they come up naturally in conversation
  - Note the quality of responses and any observations
  - Don't use this for every single exchange - only when there's something worth noting

INTERVIEW COMPLETION:
• interview_completed(overall_assessment, key_observations, interview_summary):
  - Use when you feel the conversation has reached a natural conclusion
  - Provide your overall assessment of the candidate
  - Summarize key observations and the main points discussed
  - This ends the interview session

IMPORTANT GUIDELINES:
- These are tools to support natural conversation, not rigid steps to follow
- Use them organically based on the flow of discussion
- Focus on genuine engagement rather than checking boxes
- Let the student guide some of the conversation direction
- Only track progress when there's something genuinely noteworthy
- Don't feel pressured to use every tool in every interview
"""

def inbound_handlers_register(llm):
    """
    Register simplified handlers for natural interview flow.
    """
    logger.info("Registering function handlers for natural interview flow")
    
    # Only register the simplified handlers
    llm.register_function("interview_progress_tracked", interview_progress_tracked)
    llm.register_function("interview_completed", interview_completed)
    
    logger.info("Natural interview function handlers registered successfully")

async def get_inbound_agent_context(course_id: str, agent_id: str) -> str:
    """
    Returns the dynamic context for interview agents with natural conversation approach.
    
    Args:
        course_id: ID of the course
        agent_id: ID of the agent
        
    Returns:
        str: System instruction/context for the natural interview agent
    """
    logger.info(f"Getting natural interview agent context for agent_id: {agent_id}, course_id: {course_id}")
    
    try:
        # Validate the relationship first
        logger.info("Validating agent-course relationship...")
        is_valid = await AgentContextService.validate_agent_course_relationship(course_id, agent_id)
        if not is_valid:
            logger.error(f"Invalid agent-course relationship: agent {agent_id}, course {course_id}")
            raise ValueError("Invalid agent-course relationship")
        
        logger.info("Agent-course relationship validated successfully")
        
        # Get dynamic context for natural interview
        logger.info("Fetching dynamic interview context...")
        context = await AgentContextService.get_agent_context(course_id, agent_id)
        
        # Add natural conversation guidelines
        tools_description = get_inbound_tools_description()
        full_context = f"""
        {context}

        NATURAL CONVERSATION TOOLS:
        {tools_description}

        CONVERSATION FLOW GUIDANCE:
        - YOU MUST SPEAK FIRST - Greet the student and initiate the conversation
        - Start with a warm welcome and let the student get comfortable
        - YOU are conducting the interview, asking questions, and guiding the discussion
        - The STUDENT is the one being interviewed and answering your questions
        - NEVER switch roles - you are ALWAYS the interviewer, NEVER the interviewee
        - If the student asks you questions about yourself, answer briefly then redirect to them
        - Follow their lead on topics, but YOU control the flow by asking questions
        - Gradually weave in assessment topics as the conversation naturally progresses
        - Use the tracking tool sparingly - only when you notice something particularly insightful
        - When you feel you've had a good conversation and learned about the student, use the completion tool
        - Remember: This is a conversation, not an interrogation, but YOU are the one conducting it

        Keep it natural, keep it engaging, and focus on really getting to know the student!
        """
        
        logger.info(f"Successfully loaded natural interview context for agent {agent_id}")
        return full_context.strip()
        
    except Exception as e:
        logger.error(f"Failed to get interview agent context: {e}")
        logger.exception("Full traceback:")
        
        # Fallback to a basic natural interview context
        tools_description = get_inbound_tools_description()
        fallback_context = f"""
        You are a friendly and professional interview coach who believes interviews should be conversations, not interrogations.
        You're here to get to know students and help them showcase their best selves.
        Your responses will be read aloud, so speak naturally and warmly.

        CRITICAL - YOUR ROLE:
        - You are the INTERVIEWER, NOT the interviewee
        - You conduct the interview and ask questions
        - The student/candidate is the one being interviewed
        - NEVER act as if you are the candidate being interviewed
        - NEVER answer questions as if someone is interviewing you
        - YOU ask the questions, the student answers them
        - You must always speak first when the conversation starts

        YOUR APPROACH:
        - Be genuinely interested in the student as a person
        - Start conversations with topics they're comfortable discussing
        - Ask follow-up questions that show you're listening
        - Share relevant insights or encouragement when appropriate
        - Make the experience feel supportive rather than stressful
        - Assess their knowledge and skills through natural discussion
        - Help them feel confident and engaged throughout

        CONVERSATION STYLE:
        - Use natural speech patterns: "That's really interesting!" "Tell me more about that."
        - Ask open-ended questions that get them talking
        - Build on what they share with genuine curiosity
        - Use transitions like "Speaking of that..." or "That reminds me of..."
        - Give positive reinforcement when they share good insights
        - If they seem nervous, spend time on comfortable topics first

        {tools_description}

        Remember: Your goal is to have a meaningful conversation where you learn about the student while helping them feel heard and valued. YOU are the interviewer conducting the interview.
        """.strip()
        
        logger.warning(f"Using fallback natural interview context")
        return fallback_context

def get_language_config(agent_language: str):
    """
    Get language-specific configuration for Deepgram STT, Deepgram TTS, and LLM services
    """
    language_map = {
        'en': {
            'stt_language': Language.EN_US,
            'tts_language': Language.EN,
            # 'tts_voice_id': 'Joanna',  # AWS Polly voice
            'tts_voice_id': 'aura-2-helena-en',  # Deepgram voice
            'llm_language': 'en'
        },
        'hi': {
            'stt_language': Language.HI_IN,
            'tts_language': Language.HI,
            # 'tts_voice_id': 'Aditi',  # AWS Polly Hindi voice
            'tts_voice_id': 'aura-2-andromeda-en',  # Note: Deepgram has limited Hindi voices
            'llm_language': 'hi'
        },
    }
    
    return language_map.get(agent_language, language_map['en'])

async def configure_language_services(agent_id: str):
    """
    Configure Deepgram STT and Deepgram TTS services based on agent's language
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
        # tts = AWSPollyTTSService(
        #     aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        #     api_key=config.AWS_SECRET_ACCESS_KEY,
        #     region=config.AWS_REGION,
        #     voice_id=lang_config['tts_voice_id'],
        #     params=AWSPollyTTSService.InputParams(
        #         language=lang_config['tts_language'],
        #         engine="neural" 
        # )

        # Configure Deepgram TTS
        tts = DeepgramTTSService(
            api_key=config.DEEPGRAM_STT_KEY,  
            voice=lang_config['tts_voice_id'],
            sample_rate=24000,
            encoding="linear16"
        )
        
        return stt, tts
        
    except Exception as e:
        logger.error(f"Error configuring language services: {e}")
        raise ValueError(f"Failed to configure language services: {str(e)}")