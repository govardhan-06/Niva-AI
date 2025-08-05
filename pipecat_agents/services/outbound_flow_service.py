"""
Agent: agent_llm.py
Purpose: Manages Pipecat flows for conversation logic and context.

Pending Methods: 
● prepare_context_for_call(daily_call): Prepares context for voice calls 
● save_call_summary(daily_call, summary, transcript): Saves call summaries
"""
import logging
from typing import Dict, Any, Optional, Tuple, Union
from pydantic import BaseModel
import json
import os
import time
from datetime import datetime

from pipecat_flows import (
    FlowArgs, FlowManager, FlowResult, NodeConfig, FlowsFunctionSchema
)

logger = logging.getLogger(__name__)

# Simplified result models to match the YAML structure
class EngagementResult(BaseModel):
    engagement_level: str

class ResistanceResult(BaseModel):
    resistance_type: str

class InterestResult(BaseModel):
    interest_area: Optional[str] = None

class ObjectionResult(BaseModel):
    objection_type: Optional[str] = None

class NeutraliResult(BaseModel):
    pass

class NeedsResult(BaseModel):
    primary_need: Optional[str] = None
    urgency: Optional[str] = None

class SocialProofResult(BaseModel):
    proof_type: Optional[str] = None

class ResolutionResult(BaseModel):
    resolution_method: Optional[str] = None

class ValueResult(BaseModel):
    conviction_level: Optional[str] = None

class RiskReversalResult(BaseModel):
    comfort_level: str

class ClosingResult(BaseModel):
    readiness_level: Optional[str] = None
    reason: Optional[str] = None
    objection: Optional[str] = None

class CallbackResult(BaseModel):
    callback_time: Optional[str] = None
    interest_level: Optional[str] = None

class CustomerDetailsResult(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    interest_level: Optional[str] = None
    timeline: Optional[str] = None
    notes: Optional[str] = None

# Handler functions for the simplified sales flow
async def customer_engaged(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle customer engagement."""
    engagement_level = args.get("engagement_level", "medium")
    
    flow_manager.state["engagement_level"] = engagement_level
    flow_manager.state["rapport_established"] = True
    flow_manager.state["timestamp"] = time.time()
    
    result = {
        "status": "success",
        "engagement_level": engagement_level,
        "ready_for_pitch": True
    }
    
    next_node = create_value_presentation_node()
    
    logger.info(f"✅ Customer engaged, transitioning to: {next_node["name"]}")
    return result, next_node

async def customer_resistant(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle customer resistance."""
    resistance_type = args.get("resistance_type", "uninterested")
    
    flow_manager.state["resistance_type"] = resistance_type
    flow_manager.state["needs_nurturing"] = True
    flow_manager.state["resistance_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "resistance_type": resistance_type,
        "needs_special_handling": True,
    }
    
    next_node = create_objection_handling_node()
    
    logger.info(f"✅ Customer resistant, transitioning to: {next_node["name"]}")
    return result, next_node

async def customer_interested(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle customer interest."""
    interest_area = args.get("interest_area", "general")
    
    flow_manager.state["interest_area"] = interest_area
    flow_manager.state["interest_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "interest_area": interest_area,
        "ready_for_discovery": True
    }
    
    next_node = create_needs_discovery_node()
    
    logger.info(f"✅ Customer interested, transitioning to: {next_node["name"]}")
    return result, next_node

async def customer_has_objections(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle customer objections."""
    objection_type = args.get("objection_type", "other")
    
    flow_manager.state["objection_type"] = objection_type
    flow_manager.state["objection_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "objection_type": objection_type,
        "needs_objection_handling": True
    }
    
    next_node = create_objection_handling_node()
    
    logger.info(f"✅ Customer has objections, transitioning to: {next_node["name"]}")
    return result, next_node

async def customer_neutral(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle neutral customer response."""
    flow_manager.state["neutral_response"] = True
    flow_manager.state["neutral_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "neutral_response": True,
        "needs_social_proof": True
    }
    
    next_node = create_social_proof_node()
    
    logger.info(f"✅ Customer neutral, transitioning to: {next_node["name"]}")
    return result, next_node

async def needs_identified(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle identified needs."""
    primary_need = args.get("primary_need", "unknown")
    urgency = args.get("urgency", "unclear")
    
    flow_manager.state["primary_need"] = primary_need
    flow_manager.state["urgency"] = urgency
    flow_manager.state["needs_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "primary_need": primary_need,
        "urgency": urgency,
        "ready_for_closing": True
    }
    
    if urgency in ["immediate", "soon"]:
        next_node = create_closing_attempt_node()
    else:
        next_node = create_value_justification_node()
    
    logger.info(f"✅ Needs identified, transitioning to: {next_node["name"]}")
    return result, next_node

async def needs_unclear(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle unclear needs."""
    flow_manager.state["needs_unclear"] = True
    flow_manager.state["unclear_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "needs_unclear": True,
        "needs_social_proof": True
    }
    
    next_node = create_social_proof_node()
    
    logger.info(f"✅ Needs unclear, transitioning to: {next_node["name"]}")
    return result, next_node

async def proof_convincing(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle convincing social proof."""
    proof_type = args.get("proof_type", "testimonial")
    
    flow_manager.state["proof_type"] = proof_type
    flow_manager.state["proof_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "proof_type": proof_type,
        "ready_for_closing": True
    }
    
    next_node = create_closing_attempt_node()
    
    logger.info(f"✅ Proof convincing, transitioning to: {next_node["name"]}")
    return result, next_node

async def still_hesitant(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle continued hesitation."""
    flow_manager.state["still_hesitant"] = True
    flow_manager.state["hesitant_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "still_hesitant": True,
        "needs_risk_reversal": True
    }
    
    next_node = create_risk_reversal_node()
    
    logger.info(f"✅ Still hesitant, transitioning to: {next_node["name"]}")
    return result, next_node

async def price_objection(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle price objection."""
    flow_manager.state["price_objection"] = True
    flow_manager.state["objection_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "price_objection": True,
        "needs_value_justification": True
    }
    
    next_node = create_value_justification_node()
    
    logger.info(f"✅ Price objection, transitioning to: {next_node["name"]}")
    return result, next_node

async def strong_resistance(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle strong resistance."""
    flow_manager.state["strong_resistance"] = True
    flow_manager.state["resistance_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "strong_resistance": True,
        "needs_callback_setup": True
    }
    
    next_node = create_callback_setup_node()
    
    logger.info(f"✅ Strong resistance, transitioning to: {next_node["name"]}")
    return result, next_node

async def value_understood(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle value understanding."""
    conviction_level = args.get("conviction_level", "medium")
    
    flow_manager.state["conviction_level"] = conviction_level
    flow_manager.state["value_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "conviction_level": conviction_level,
        "ready_for_closing": True
    }
    
    if conviction_level == "high":
        next_node = create_closing_attempt_node()
    else:
        next_node = create_risk_reversal_node()
    
    logger.info(f"✅ Value understood, transitioning to: {next_node["name"]}")
    return result, next_node

async def still_price_sensitive(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle continued price sensitivity."""
    flow_manager.state["price_sensitive"] = True
    flow_manager.state["price_sensitivity_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "price_sensitive": True,
        "needs_risk_reversal": True
    }
    
    next_node = create_risk_reversal_node()
    
    logger.info(f"✅ Still price sensitive, transitioning to: {next_node["name"]}")
    return result, next_node

async def risk_comfort_achieved(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle risk comfort achievement."""
    comfort_level = args.get("comfort_level", "medium")
    
    flow_manager.state["risk_comfort_level"] = comfort_level
    flow_manager.state["comfort_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "comfort_level": comfort_level,
        "ready_for_closing": True
    }
    
    if comfort_level == "high":
        next_node = create_closing_attempt_node()
    else:
        next_node = create_objection_handling_node()
    
    logger.info(f"✅ Risk comfort achieved, transitioning to: {next_node["name"]}")
    return result, next_node

async def needs_more_assurance(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle need for more assurance."""
    flow_manager.state["needs_assurance"] = True
    flow_manager.state["assurance_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "needs_assurance": True,
        "needs_callback_setup": True
    }
    
    next_node = create_callback_setup_node()
    
    logger.info(f"✅ Needs more assurance, transitioning to: {next_node["name"]}")
    return result, next_node

async def needs_time(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle time request."""
    reason = args.get("reason", "other")
    
    flow_manager.state["time_reason"] = reason
    flow_manager.state["time_request_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "reason": reason,
        "needs_callback_setup": True
    }
    
    next_node = create_callback_setup_node()
    
    logger.info(f"✅ Needs time, transitioning to: {next_node["name"]}")
    return result, next_node

async def final_objection(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle final objection."""
    objection = args.get("objection", "general concern")
    
    flow_manager.state["final_objection"] = objection
    flow_manager.state["final_objection_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "objection": objection,
        "needs_objection_handling": True
    }
    
    next_node = create_objection_handling_node()
    
    logger.info(f"✅ Final objection, transitioning to: {next_node["name"]}")
    return result, next_node

async def no_callback_interest(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle no callback interest."""
    flow_manager.state["no_callback"] = True
    flow_manager.state["no_callback_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "no_callback": True,
        "ready_for_polite_close": True
    }
    
    next_node = create_polite_close_node()
    
    logger.info(f"✅ No callback interest, transitioning to: {next_node["name"]}")
    return result, next_node

async def objection_resolved(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle resolved objection."""
    resolution_method = args.get("resolution_method", "logic")
    
    flow_manager.state["resolution_method"] = resolution_method
    flow_manager.state["objection_resolved_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "resolution_method": resolution_method,
        "ready_for_closing": True
    }
    
    next_node = create_closing_attempt_node()
    
    logger.info(f"✅ Objection resolved, transitioning to: {next_node["name"]}")
    return result, next_node

async def customer_ready(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle ready customer."""
    readiness_level = args.get("readiness_level", "ready")
    
    flow_manager.state["readiness_level"] = readiness_level
    flow_manager.state["ready_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "readiness_level": readiness_level,
        "ready_for_contact_collection": True
    }
    
    next_node = create_contact_collection_node()
    
    logger.info(f"✅ Customer ready, transitioning to: {next_node["name"]}")
    return result, next_node

async def callback_scheduled(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle scheduled callback."""
    callback_time = args.get("callback_time", "later")
    interest_level = args.get("interest_level", "medium")
    
    flow_manager.state["callback_time"] = callback_time
    flow_manager.state["interest_level"] = interest_level
    flow_manager.state["callback_timestamp"] = time.time()
    
    result = {
        "status": "success",
        "callback_time": callback_time,
        "interest_level": interest_level,
        "ready_for_contact_collection": True
    }
    
    next_node = create_contact_collection_node()
    
    logger.info(f"✅ Callback scheduled, transitioning to: {next_node["name"]}")
    return result, next_node

async def get_customer_details(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle customer details collection."""
    name = args.get("name", "")
    phone = args.get("phone", "")
    email = args.get("email", "")
    
    customer_data = {
        "name": name,
        "phone": phone,
        "email": email,
        "interest_level": args.get("interest_level"),
        "timeline": args.get("timeline"),
        "notes": args.get("notes"),
        "collected_at": datetime.now().isoformat()
    }
    
    # Store customer details in flow state instead of file
    flow_manager.state["customer_details"] = customer_data
    flow_manager.state["details_collected_timestamp"] = time.time()
    flow_manager.state["contact_collection_completed"] = True
    
    logger.info(f"✅ Customer details stored in flow state: {customer_data}")
    
    result = {
        "status": "success",
        "name": name,
        "phone": phone,
        "email": email,
        "ready_for_successful_close": True
    }
    
    next_node = create_successful_close_node()
    
    logger.info(f"✅ Customer details collected, transitioning to: {next_node["name"]}")
    return result, next_node

# Node creation functions for the simplified flow
def create_rapport_building_node() -> NodeConfig:
    """Create the initial rapport building node."""
    return NodeConfig(
        name="rapport_building",
        task_messages=[
            {
                "role": "user",
                "content": "Greet the customer warmly, introduce yourself, and use rapport-building techniques like asking about their day. Create a comfortable atmosphere before mentioning your offering.",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="customer_engaged",
                description="Customer responds positively and seems open",
                properties={
                    "engagement_level": {
                        "type": "string",
                        "enum": ["high", "medium", "low"]
                    }
                },
                required=["engagement_level"],
                handler=customer_engaged,
            ),
            FlowsFunctionSchema(
                name="customer_resistant",
                description="Customer seems resistant, busy, or uninterested",
                properties={
                    "resistance_type": {
                        "type": "string",
                        "enum": ["busy", "suspicious", "uninterested"]
                    }
                },
                required=["resistance_type"],
                handler=customer_resistant,
            )
        ],
    )

def create_value_presentation_node() -> NodeConfig:
    """Create value presentation node."""
    return NodeConfig(
        name="value_presentation",
        task_messages=[
            {
                "role": "user",
                "content": "Present your core value proposition focusing on benefits, not features. Use the problem-solution framework and ask engaging questions to involve them in the conversation.",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="customer_interested",
                description="Customer shows genuine interest or asks questions",
                properties={
                    "interest_area": {
                        "type": "string",
                        "description": "What aspect interested them most"
                    }
                },
                required=["interest_area"],
                handler=customer_interested,
            ),
            FlowsFunctionSchema(
                name="customer_has_objections",
                description="Customer expresses concerns or objections",
                properties={
                    "objection_type": {
                        "type": "string",
                        "enum": ["price", "timing", "need", "trust", "other"]
                    }
                },
                required=["objection_type"],
                handler=customer_has_objections,
            ),
            FlowsFunctionSchema(
                name="customer_neutral",
                description="Customer listening but not showing strong reaction",
                properties={},
                required=[],
                handler=customer_neutral,
            )
        ],
    )

def create_needs_discovery_node() -> NodeConfig:
    """Create needs discovery node."""
    return NodeConfig(
        name="needs_discovery",
        task_messages=[
            {
                "role": "user",
                "content": "Ask open-ended questions to understand their specific needs, challenges, and timeline. Listen actively and use their responses to tailor your approach.",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="needs_identified",
                description="Customer's needs are clearly understood",
                properties={
                    "primary_need": {
                        "type": "string",
                        "description": "Their main need or challenge"
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["immediate", "soon", "flexible", "unclear"]
                    }
                },
                required=["primary_need", "urgency"],
                handler=needs_identified,
            ),
            FlowsFunctionSchema(
                name="needs_unclear",
                description="Customer's needs are still unclear or they're evasive",
                properties={},
                required=[],
                handler=needs_unclear,
            )
        ],
    )

def create_social_proof_node() -> NodeConfig:
    """Create social proof node."""
    return NodeConfig(
        name="social_proof",
        task_messages=[
            {
                "role": "user",
                "content": "Share success stories, testimonials, or statistics from similar customers. Create credibility and show the value others have received.",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="proof_convincing",
                description="Customer responds positively to social proof",
                properties={
                    "proof_type": {
                        "type": "string",
                        "enum": ["testimonial", "statistics", "case_study"]
                    }
                },
                required=["proof_type"],
                handler=proof_convincing,
            ),
            FlowsFunctionSchema(
                name="still_hesitant",
                description="Customer remains hesitant despite social proof",
                properties={},
                required=[],
                handler=still_hesitant,
            )
        ],
    )

def create_objection_handling_node() -> NodeConfig:
    """Create objection handling node."""
    return NodeConfig(
        name="objection_handling",
        task_messages=[
            {
                "role": "user",
                "content": "Address objections using the 'acknowledge-relate-resolve' approach. Listen to their concern, show understanding, and provide a solution or reframe.",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="objection_resolved",
                description="Customer accepts your response to their objection",
                properties={
                    "resolution_method": {
                        "type": "string",
                        "enum": ["logic", "emotion", "proof", "reframe"]
                    }
                },
                required=["resolution_method"],
                handler=objection_resolved,
            ),
            FlowsFunctionSchema(
                name="price_objection",
                description="Customer specifically objects to price",
                properties={},
                required=[],
                handler=price_objection,
            ),
            FlowsFunctionSchema(
                name="strong_resistance",
                description="Customer shows strong resistance",
                properties={},
                required=[],
                handler=strong_resistance,
            )
        ],
    )

def create_value_justification_node() -> NodeConfig:
    """Create value justification node."""
    return NodeConfig(
        name="value_justification",
        task_messages=[
            {
                "role": "user",
                "content": "Reframe price concerns by focusing on value, ROI, and cost of inaction. Break down costs and show the investment perspective.",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="value_understood",
                description="Customer understands the value proposition",
                properties={
                    "conviction_level": {
                        "type": "string",
                        "enum": ["high", "medium", "low"]
                    }
                },
                required=["conviction_level"],
                handler=value_understood,
            ),
            FlowsFunctionSchema(
                name="still_price_sensitive",
                description="Customer still concerned about price",
                properties={},
                required=[],
                handler=still_price_sensitive,
            )
        ],
    )

def create_risk_reversal_node() -> NodeConfig:
    """Create risk reversal node."""
    return NodeConfig(
        name="risk_reversal",
        task_messages=[
            {
                "role": "user",
                "content": "Offer guarantees, trials, or easy cancellation to remove risk from their decision. Make it safe for them to say yes.",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="risk_comfort_achieved",
                description="Customer feels comfortable with risk reversal",
                properties={
                    "comfort_level": {
                        "type": "string",
                        "enum": ["high", "medium", "low"]
                    }
                },
                required=["comfort_level"],
                handler=risk_comfort_achieved,
            ),
            FlowsFunctionSchema(
                name="needs_more_assurance",
                description="Customer needs additional assurance",
                properties={},
                required=[],
                handler=needs_more_assurance,
            )
        ],
    )

def create_closing_attempt_node() -> NodeConfig:
    """Create closing attempt node."""
    return NodeConfig(
        name="closing_attempt",
        task_messages=[
            {
                "role": "user",
                "content": "Use assumptive closing techniques. Ask about next steps, implementation, or preferences rather than asking if they want to buy.",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="customer_ready",
                description="Customer indicates readiness to proceed",
                properties={
                    "readiness_level": {
                        "type": "string",
                        "enum": ["very_ready", "ready", "somewhat_ready"]
                    }
                },
                required=["readiness_level"],
                handler=customer_ready,
            ),
            FlowsFunctionSchema(
                name="needs_time",
                description="Customer asks for time to think or needs approval",
                properties={
                    "reason": {
                        "type": "string",
                        "enum": ["think_it_over", "discuss_with_spouse", "financial_planning", "other"]
                    }
                },
                required=["reason"],
                handler=needs_time,
            ),
            FlowsFunctionSchema(
                name="final_objection",
                description="Customer raises a final objection",
                properties={
                    "objection": {
                        "type": "string",
                        "description": "Their final concern"
                    }
                },
                required=["objection"],
                handler=final_objection,
            )
        ],
    )

def create_callback_setup_node() -> NodeConfig:
    """Create callback setup node that directly transitions to contact collection."""
    return NodeConfig(
        name="callback_setup",
        task_messages=[
            {
                "role": "user",
                "content": """The customer has indicated they want a callback or follow-up. Your goal is to:

1. Acknowledge their request positively
2. Get the timing for the callback 
3. Assess their interest level
4. Immediately transition to collecting their contact information

Say something like: "Absolutely! I'd be happy to call you back. When would be a good time for you?" 

Once they give you a time preference, immediately call the callback_scheduled function which will move us to collect their contact details.""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="callback_scheduled",
                description="Customer commits to a follow-up - use this immediately when they indicate when they want to be called back",
                properties={
                    "callback_time": {
                        "type": "string",
                        "description": "When they agreed to follow up (e.g., 'tomorrow afternoon', 'next week', 'in a few days')"
                    },
                    "interest_level": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Assess their level of interest based on how they responded"
                    }
                },
                required=["callback_time", "interest_level"],
                handler=callback_scheduled,
            ),
            FlowsFunctionSchema(
                name="no_callback_interest",
                description="Customer not interested in follow-up - only use if they explicitly refuse a callback",
                properties={},
                required=[],
                handler=no_callback_interest,
            )
        ],
    )

def create_contact_collection_node() -> NodeConfig:
    """Create contact collection node that handles both purchase and callback scenarios."""
    logger.info("=== CREATING CONTACT COLLECTION NODE ===")
    return NodeConfig(
        name="contact_collection",
        task_messages=[
            {
                "role": "user",
                "content": """You are now in the contact collection phase. Your goal is to naturally collect the customer's contact information.

                If this is for a CALLBACK (check flow state for callback_requested or callback_time):
                Say something like: "Perfect! Let me get your contact information so I can call you back at the right time. Can I get your full name and the best phone number to reach you?"

                If this is for a PURCHASE (customer ready to buy):
                Say something like: "Excellent! Let me get your contact information so we can move forward with this. Can I get your full name and the best phone number to reach you?"

                Then collect:
                - Full name (required)
                - Phone number (required) 
                - Email address (optional but recommended)
                - Their interest level (very_high, high, medium, low)
                - Their timeline (immediate, within_week, within_month, flexible)
                - Any special notes or requirements

                Once you have at least their name and phone number, call the get_customer_details function to save this information.""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="get_customer_details",
                description="Collect customer contact and preference information - CALL THIS when you have the customer's name and phone number",
                properties={
                    "name": {
                        "type": "string",
                        "description": "Customer's full name"
                    },
                    "phone": {
                        "type": "string",
                        "description": "Customer's phone number"
                    },
                    "email": {
                        "type": "string",
                        "description": "Customer's email address"
                    },
                    "interest_level": {
                        "type": "string",
                        "enum": ["very_high", "high", "medium", "low"],
                        "description": "Customer's level of interest"
                    },
                    "timeline": {
                        "type": "string",
                        "enum": ["immediate", "within_week", "within_month", "flexible"],
                        "description": "Customer's timeline for implementation"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Any special notes, callback preferences, or requirements mentioned by the customer"
                    }
                },
                required=["name", "phone"],
                handler=get_customer_details,
            )
        ],
    )

def create_successful_close_node() -> NodeConfig:
    """Create successful close node."""
    return NodeConfig(
        name="successful_close",
        task_messages=[
            {
                "role": "user",
                "content": "Confirm next steps, thank them for their time, and create positive anticipation for follow-up. End professionally and warmly.",
            }
        ],
        functions=[],
    )

def create_polite_close_node() -> NodeConfig:
    """Create polite close node."""
    return NodeConfig(
        name="polite_close",
        task_messages=[
            {
                "role": "user",
                "content": "Thank them for their time, leave the door open for future opportunities, and end the conversation professionally and positively.",
            }
        ],
        functions=[],
    )

def get_sales_flow_config() -> Dict[str, Any]:
    """Get the simplified sales flow configuration matching the YAML."""
    return {
        "initial_node": "rapport_building",
        "turn_manager": {
            "type": "basic",
            "timeout": 30
        },
        "nodes": {
            "rapport_building": create_rapport_building_node(),
            "value_presentation": create_value_presentation_node(),
            "needs_discovery": create_needs_discovery_node(),
            "social_proof": create_social_proof_node(),
            "objection_handling": create_objection_handling_node(),
            "value_justification": create_value_justification_node(),
            "risk_reversal": create_risk_reversal_node(),
            "closing_attempt": create_closing_attempt_node(),
            "callback_setup": create_callback_setup_node(),
            "contact_collection": create_contact_collection_node(),
            "successful_close": create_successful_close_node(),
            "polite_close": create_polite_close_node(),
        }
    }