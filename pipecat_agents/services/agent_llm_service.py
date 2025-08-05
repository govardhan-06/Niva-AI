import logging
from pipecat_agents.services.agent_context import AgentContextService

from pipecat_agents.services.outbound_flow_service import (
    customer_engaged,
    customer_resistant,
    customer_interested,
    customer_has_objections,
    customer_neutral,
    needs_identified,
    needs_unclear,
    proof_convincing,
    still_hesitant,
    objection_resolved,
    price_objection,
    strong_resistance,
    value_understood,
    still_price_sensitive,
    risk_comfort_achieved,
    needs_more_assurance,
    customer_ready,
    needs_time,
    final_objection,
    callback_scheduled,
    no_callback_interest,
    get_customer_details
)

from pipecat_agents.services.inbound_flow_service import (
    call_routing,
    customer_info_collected,
    complaint_logged,
    inquiry_processed,
    technical_issue_diagnosed,
    issue_resolved,
    escalation_required,
    follow_up_scheduled,
    emergency_handled,
    save_interaction_data
)
from pipecat.services.google.stt import GoogleSTTService
from pipecat.services.google.tts import GoogleTTSService
from pipecat.transcriptions.language import Language

from app import config

logger = logging.getLogger(__name__)

def get_outbound_tools_description():
    """Get description of available tools for outbound agents."""
    return """
AVAILABLE TOOLS - Use these to advance the conversation based on customer responses:

RAPPORT BUILDING:
• customer_engaged(engagement_level): When customer responds positively and seems open to conversation
• customer_resistant(resistance_type): When customer seems busy, suspicious, or uninterested

VALUE PRESENTATION:
• customer_interested(interest_area): When customer shows genuine interest or asks questions
• customer_has_objections(objection_type): When customer expresses concerns (price, timing, need, trust, other)
• customer_neutral(): When customer is listening but not showing strong reaction

NEEDS DISCOVERY:
• needs_identified(primary_need, urgency): When customer's needs are clearly understood
• needs_unclear(): When customer's needs are still unclear or they're evasive

SOCIAL PROOF:
• proof_convincing(proof_type): When customer responds positively to testimonials/case studies
• still_hesitant(): When customer remains hesitant despite social proof

OBJECTION HANDLING:
• objection_resolved(resolution_method): When customer accepts your response to their objection
• price_objection(): When customer specifically objects to price
• strong_resistance(): When customer shows strong resistance

VALUE JUSTIFICATION:
• value_understood(conviction_level): When customer understands the value proposition
• still_price_sensitive(): When customer still concerned about price

RISK REVERSAL:
• risk_comfort_achieved(comfort_level): When customer feels comfortable with guarantees/trials
• needs_more_assurance(): When customer needs additional assurance

CLOSING:
• customer_ready(readiness_level): When customer indicates readiness to proceed
• needs_time(reason): When customer asks for time to think or needs approval
• final_objection(objection): When customer raises a final concern

CALLBACK & CONTACT:
• callback_scheduled(callback_time, interest_level): When customer commits to follow-up
• no_callback_interest(): When customer not interested in follow-up (only if explicitly refused)
• get_customer_details(name, phone, email, interest_level, timeline, notes): Collect contact information

IMPORTANT: Always call the appropriate function based on customer responses to advance the conversation flow.
"""

def get_inbound_tools_description():
    """Get description of available tools for inbound agents."""
    return """
AVAILABLE TOOLS - Use these to handle customer service requests effectively:

CALL ROUTING:
• call_routing(call_type, urgency): Route calls based on customer needs (complaint, technical_support, billing_inquiry, general_inquiry, emergency)

INFORMATION COLLECTION:
• customer_info_collected(account_number, customer_name, phone_number, email): After collecting customer information for verification

COMPLAINT HANDLING:
• complaint_logged(complaint_category, severity, description): Document customer complaints (service_quality, billing_error, technical_issue, staff_behavior, service_outage, other)

INQUIRIES:
• inquiry_processed(inquiry_type, specific_question): Handle general questions (hours, location, services, pricing, account_status, billing, policies, other)

TECHNICAL SUPPORT:
• technical_issue_diagnosed(issue_category, device_type, error_description): Diagnose technical problems (password_reset, account_settings, app_issue, connectivity, hardware_failure, network_outage, other)

RESOLUTION:
• issue_resolved(resolution_type, customer_satisfaction, follow_up_needed): When issue is successfully resolved
• escalation_required(escalation_reason, department, notes): When issue needs escalation to specialists

FOLLOW-UP:
• follow_up_scheduled(follow_up_type, timeframe, contact_method): Schedule follow-up calls or callbacks

EMERGENCY:
• emergency_handled(emergency_type, immediate_action): Handle emergency situations

DATA MANAGEMENT:
• save_interaction_data(interaction_summary, satisfaction_rating): Save complete interaction summary at call end

IMPORTANT: Use these functions to properly categorize, route, and resolve customer issues while maintaining detailed records.
"""

def outbound_handlers_register(llm):
    """
    Register handlers for outbound cases - simplified for new flow.
    """
    logger.info("Registering simplified function handlers for sales flow")
    
    # Rapport building handlers
    llm.register_function("customer_engaged", customer_engaged)
    llm.register_function("customer_resistant", customer_resistant)
    
    # Value presentation handlers
    llm.register_function("customer_interested", customer_interested)
    llm.register_function("customer_has_objections", customer_has_objections)
    llm.register_function("customer_neutral", customer_neutral)
    
    # Needs discovery handlers
    llm.register_function("needs_identified", needs_identified)
    llm.register_function("needs_unclear", needs_unclear)
    
    # Social proof handlers
    llm.register_function("proof_convincing", proof_convincing)
    llm.register_function("still_hesitant", still_hesitant)
    
    # Objection handling handlers
    llm.register_function("objection_resolved", objection_resolved)
    llm.register_function("price_objection", price_objection)
    llm.register_function("strong_resistance", strong_resistance)
    
    # Value justification handlers
    llm.register_function("value_understood", value_understood)
    llm.register_function("still_price_sensitive", still_price_sensitive)
    
    # Risk reversal handlers
    llm.register_function("risk_comfort_achieved", risk_comfort_achieved)
    llm.register_function("needs_more_assurance", needs_more_assurance)
    
    # Closing attempt handlers
    llm.register_function("customer_ready", customer_ready)
    llm.register_function("needs_time", needs_time)
    llm.register_function("final_objection", final_objection)
    
    # Callback setup handlers
    llm.register_function("callback_scheduled", callback_scheduled)
    llm.register_function("no_callback_interest", no_callback_interest)
    
    # Contact collection handlers
    llm.register_function("get_customer_details", get_customer_details)
    
    logger.info("All simplified function handlers registered successfully")

def inbound_handlers_register(llm):
    """
    Register handlers for inbound customer service cases.
    """
    logger.info("Registering function handlers for inbound customer service flow")
    
    # Call routing handlers
    llm.register_function("call_routing", call_routing)
    
    # Customer information handlers
    llm.register_function("customer_info_collected", customer_info_collected)
    
    # Complaint handling handlers
    llm.register_function("complaint_logged", complaint_logged)
    
    # Inquiry processing handlers
    llm.register_function("inquiry_processed", inquiry_processed)
    
    # Technical support handlers
    llm.register_function("technical_issue_diagnosed", technical_issue_diagnosed)
    
    # Resolution handlers
    llm.register_function("issue_resolved", issue_resolved)
    
    # Escalation handlers
    llm.register_function("escalation_required", escalation_required)
    
    # Follow-up handlers
    llm.register_function("follow_up_scheduled", follow_up_scheduled)
    
    # Emergency handlers
    llm.register_function("emergency_handled", emergency_handled)
    
    # Data saving handlers
    llm.register_function("save_interaction_data", save_interaction_data)
    
    logger.info("All inbound function handlers registered successfully")

async def get_agent_context(company_id: str, agent_id: str) -> str:
    """
    Returns the dynamic context for the agent based on company and agent IDs.
    
    Args:
        company_id: ID of the company
        agent_id: ID of the agent
        
    Returns:
        str: System instruction/context for the agent
    """
    logger.info(f"PipecatAgentRunner: Getting agent context for agent_id: {agent_id}, company_id: {company_id}")
    
    try:
        # Validate the relationship first
        logger.info("Validating agent-company relationship...")
        is_valid = await AgentContextService.validate_agent_company_relationship(company_id, agent_id)
        if not is_valid:
            logger.error(f"Invalid agent-company relationship: agent {agent_id}, company {company_id}")
            raise ValueError("Invalid agent-company relationship")
        
        logger.info("Agent-company relationship validated successfully")
        
        # Get dynamic context
        logger.info("Fetching dynamic context...")
        context = await AgentContextService.get_agent_context(company_id, agent_id)
        
        # Add outbound tools description
        # tools_description = get_outbound_tools_description()
        # full_context = f"{context}\n\n{tools_description}"
        full_context=context
        
        logger.info(f"Successfully loaded context for agent {agent_id} in company {company_id}")
        logger.info(f"Context length: {len(full_context)} characters")
        
        # Log a sample of the context for verification
        logger.info(f"Context sample: {full_context[:300]}...")
        
        return full_context
        
    except Exception as e:
        logger.error(f"Failed to get agent context: {e}")
        logger.exception("Full traceback:")
        
        # Fallback to a basic context with tools
        tools_description = get_outbound_tools_description()
        fallback_context = f"""
            You are a professional sales representative conducting outbound calls. 
            You're trained to build rapport, present value, and guide prospects through the sales process.
            Your responses will be read aloud, so keep them natural and conversational.
            Be helpful, patient, and focused on understanding customer needs.
            
            {tools_description}
        """.strip()
        
        logger.warning(f"Using fallback outbound context with tools")
        return fallback_context

async def get_inbound_agent_context(company_id: str, agent_id: str) -> str:
    """
    Returns the dynamic context for inbound agents.
    
    Args:
        company_id: ID of the company
        agent_id: ID of the agent
        
    Returns:
        str: System instruction/context for the inbound agent
    """
    logger.info(f"PipecatAgentRunner: Getting inbound agent context for agent_id: {agent_id}, company_id: {company_id}")
    
    try:
        # Validate the relationship first
        logger.info("Validating agent-company relationship...")
        is_valid = await AgentContextService.validate_agent_company_relationship(company_id, agent_id)
        if not is_valid:
            logger.error(f"Invalid agent-company relationship: agent {agent_id}, company {company_id}")
            raise ValueError("Invalid agent-company relationship")
        
        logger.info("Agent-company relationship validated successfully")
        
        # Get dynamic context - the AgentContextService already handles inbound/outbound detection
        logger.info("Fetching dynamic inbound context...")
        context = await AgentContextService.get_agent_context(company_id, agent_id)
        
        # Add inbound tools description
        # tools_description = get_inbound_tools_description()
        # full_context = f"{context}\n\n{tools_description}"
        full_context=context
        
        logger.info(f"Successfully loaded inbound context for agent {agent_id}")
        return full_context
        
    except Exception as e:
        logger.error(f"Failed to get inbound agent context: {e}")
        logger.exception("Full traceback:")
        
        # Fallback to a basic inbound context with tools
        tools_description = get_inbound_tools_description()
        fallback_context = f"""
        You are a professional customer service representative handling inbound calls.
        You're trained to assist customers with complaints, technical issues, billing inquiries, and general questions.
        Your responses will be read aloud, so keep them natural and conversational.
        Be empathetic, patient, and focused on resolving customer issues effectively.
        Always maintain a helpful and professional demeanor.
        
        {tools_description}
        """.strip()
        
        logger.warning(f"Using fallback inbound context with tools")
        return fallback_context

def get_language_config(agent_language: str):
    """
    Get language-specific configuration for STT, TTS, and LLM services
    
    Args:
        agent_language: Language code from agent model (e.g., 'en', 'hi')
        
    Returns:
        dict: Configuration dictionary with:
            - stt_language: Language for speech-to-text
            - tts_language: Language for text-to-speech
            - tts_voice_id: Voice ID for TTS
            - llm_language: Language for LLM
    """
    language_map = {
        'en': {
            'stt_language': Language.EN_US,
            'tts_language': Language.EN_US,
            'tts_voice_id': 'en-US-Chirp3-HD-Achernar',
            'stt_model': 'chirp_2',
            'stt_location': 'us-central1',
            'enable_automatic_punctuation': True,
            'llm_language': 'en'
        },
        'hi': {
            'stt_language': Language.HI_IN,
            'tts_language': Language.HI_IN,
            'tts_voice_id': 'hi-IN-Chirp3-HD-Achernar',
            'stt_model': 'latest_long',
            'stt_location': 'global',
            'enable_automatic_punctuation': False,
            'llm_language': 'hi'
        },
        'ml': {
            'stt_language': [Language.ML_IN, Language.EN_US],
            'tts_language': Language.ML_IN,
            'tts_voice_id': 'ml-IN-Chirp3-HD-Achernar',
            'stt_model': 'latest_long',
            'stt_location': 'global',
            'enable_automatic_punctuation': False,
            'llm_language': 'ml'
        },
        'ta': {
            'stt_language': [Language.TA_IN, Language.EN_US],
            'tts_language': Language.TA_IN,
            'tts_voice_id': 'ta-IN-Chirp3-HD-Achernar',
            'stt_model': 'latest_long',
            'stt_location': 'global',
            'enable_automatic_punctuation': False,
            'llm_language': 'ta'
        }
    }
    
    # Default to English if language not found
    return language_map.get(agent_language, language_map['en'])

async def configure_language_services(agent_id: str):
    """
    Configure STT, TTS  services based on agent's language
    
    Args:
        agent_id: ID of the agent
        
    Returns:
        tuple: (stt_service, tts_service)
    """
    try:
        # Get agent's language
        agent_language = await AgentContextService.get_default_lang(agent_id)
        lang_config = get_language_config(agent_language)
        
        logger.info(f"Configuring services for language: {agent_language}")
        
        # Configure STT
        stt = GoogleSTTService(
            credentials_path="./custard-ai-2c1433df2722.json",
            location=lang_config["stt_location"],
            params=GoogleSTTService.InputParams(
                languages=lang_config['stt_language'],
                model=lang_config["stt_model"],
                enable_automatic_punctuation=lang_config['enable_automatic_punctuation'],
                enable_interim_results=True
            )
        )
        
        # Configure TTS
        tts = GoogleTTSService(
            credentials_path="./custard-ai-2c1433df2722.json",
            voice_id=lang_config['tts_voice_id'],
            params=GoogleTTSService.InputParams(
                language=lang_config['tts_language'],
                google_style="empathetic",
            )
        )
        
        return stt, tts
        
    except Exception as e:
        logger.error(f"Error configuring language services: {e}")
        raise ValueError(f"Failed to configure language services: {str(e)}")