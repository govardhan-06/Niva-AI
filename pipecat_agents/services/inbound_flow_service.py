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

# Result models for inbound customer service flow
class CallTypeResult(BaseModel):
    call_type: str
    urgency: Optional[str] = None

class CustomerInfoResult(BaseModel):
    account_number: Optional[str] = None
    customer_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None

class ComplaintResult(BaseModel):
    complaint_category: str
    severity: str
    description: Optional[str] = None

class InquiryResult(BaseModel):
    inquiry_type: str
    specific_question: Optional[str] = None

class TechnicalIssueResult(BaseModel):
    issue_category: str
    device_type: Optional[str] = None
    error_description: Optional[str] = None

class ResolutionResult(BaseModel):
    resolution_type: str
    customer_satisfaction: Optional[str] = None
    follow_up_needed: Optional[bool] = None

class EscalationResult(BaseModel):
    escalation_reason: str
    department: str
    notes: Optional[str] = None

class FollowUpResult(BaseModel):
    follow_up_type: str
    timeframe: Optional[str] = None
    contact_method: Optional[str] = None

# Handler functions for inbound customer service flow
async def call_routing(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Route the call based on customer needs."""
    call_type = args.get("call_type", "general")
    urgency = args.get("urgency", "normal")
    
    flow_manager.state["call_type"] = call_type
    flow_manager.state["urgency"] = urgency
    flow_manager.state["call_start_time"] = time.time()
    
    result = {
        "status": "success",
        "call_type": call_type,
        "urgency": urgency
    }
    
    # Route to appropriate next node based on call type
    if call_type == "complaint":
        next_node = create_customer_info_collection_node()
    elif call_type == "technical_support":
        next_node = create_customer_info_collection_node()
    elif call_type == "billing_inquiry":
        next_node = create_customer_info_collection_node()
    elif call_type == "general_inquiry":
        next_node = create_general_inquiry_node()
    elif call_type == "emergency":
        next_node = create_emergency_handling_node()
    else:
        next_node = create_customer_info_collection_node()
    
    logger.info(f"✅ Call routed - Type: {call_type}, transitioning to: {next_node['name']}")
    return result, next_node

async def customer_info_collected(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle customer information collection."""
    account_number = args.get("account_number")
    customer_name = args.get("customer_name")
    phone_number = args.get("phone_number")
    email = args.get("email")
    
    customer_info = {
        "account_number": account_number,
        "customer_name": customer_name,
        "phone_number": phone_number,
        "email": email,
        "verified": True if account_number else False
    }
    
    flow_manager.state["customer_info"] = customer_info
    flow_manager.state["info_collected_time"] = time.time()
    
    result = {
        "status": "success",
        "customer_verified": customer_info["verified"],
        **customer_info
    }
    
    # Route based on original call type
    call_type = flow_manager.state.get("call_type", "general")
    
    if call_type == "complaint":
        next_node = create_complaint_handling_node()
    elif call_type == "technical_support":
        next_node = create_technical_support_node()
    elif call_type == "billing_inquiry":
        next_node = create_billing_inquiry_node()
    else:
        next_node = create_general_inquiry_node()
    
    logger.info(f"✅ Customer info collected, transitioning to: {next_node['name']}")
    return result, next_node

async def complaint_logged(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle complaint logging."""
    complaint_category = args.get("complaint_category", "other")
    severity = args.get("severity", "medium")
    description = args.get("description", "")
    
    complaint_data = {
        "category": complaint_category,
        "severity": severity,
        "description": description,
        "logged_time": time.time()
    }
    
    flow_manager.state["complaint"] = complaint_data
    
    result = {
        "status": "success",
        "complaint_category": complaint_category,
        "severity": severity,
        "needs_immediate_action": severity in ["high", "critical"]
    }
    
    # Route based on severity and category
    if severity in ["high", "critical"]:
        next_node = create_escalation_node()
    elif complaint_category in ["billing_error", "service_outage"]:
        next_node = create_immediate_resolution_node()
    else:
        next_node = create_complaint_resolution_node()
    
    logger.info(f"✅ Complaint logged - Category: {complaint_category}, Severity: {severity}")
    return result, next_node

async def inquiry_processed(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle general inquiry processing."""
    inquiry_type = args.get("inquiry_type", "general")
    specific_question = args.get("specific_question", "")
    
    inquiry_data = {
        "type": inquiry_type,
        "question": specific_question,
        "processed_time": time.time()
    }
    
    flow_manager.state["inquiry"] = inquiry_data
    
    result = {
        "status": "success",
        "inquiry_type": inquiry_type,
        "can_provide_immediate_answer": inquiry_type in ["hours", "location", "services", "pricing"]
    }
    
    # Route based on inquiry complexity
    if inquiry_type in ["hours", "location", "services", "pricing"]:
        next_node = create_information_provision_node()
    elif inquiry_type in ["account_status", "billing"]:
        next_node = create_account_specific_inquiry_node()
    else:
        next_node = create_escalation_node()
    
    logger.info(f"✅ Inquiry processed - Type: {inquiry_type}")
    return result, next_node

async def technical_issue_diagnosed(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle technical issue diagnosis."""
    issue_category = args.get("issue_category", "other")
    device_type = args.get("device_type")
    error_description = args.get("error_description", "")
    
    technical_data = {
        "category": issue_category,
        "device": device_type,
        "error": error_description,
        "diagnosed_time": time.time()
    }
    
    flow_manager.state["technical_issue"] = technical_data
    
    result = {
        "status": "success",
        "issue_category": issue_category,
        "can_resolve_remotely": issue_category in ["password_reset", "account_settings", "app_issue"]
    }
    
    # Route based on issue complexity
    if issue_category in ["password_reset", "account_settings", "app_issue"]:
        next_node = create_technical_resolution_node()
    elif issue_category in ["hardware_failure", "network_outage"]:
        next_node = create_escalation_node()
    else:
        next_node = create_technical_troubleshooting_node()
    
    logger.info(f"✅ Technical issue diagnosed - Category: {issue_category}")
    return result, next_node

async def issue_resolved(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle successful issue resolution."""
    resolution_type = args.get("resolution_type", "standard")
    customer_satisfaction = args.get("customer_satisfaction", "satisfied")
    follow_up_needed = args.get("follow_up_needed", False)
    
    resolution_data = {
        "type": resolution_type,
        "satisfaction": customer_satisfaction,
        "follow_up": follow_up_needed,
        "resolved_time": time.time()
    }
    
    flow_manager.state["resolution"] = resolution_data
    
    result = {
        "status": "success",
        "resolution_type": resolution_type,
        "customer_satisfaction": customer_satisfaction,
        "follow_up_needed": follow_up_needed
    }
    
    if follow_up_needed:
        next_node = create_follow_up_scheduling_node()
    else:
        next_node = create_call_completion_node()
    
    logger.info(f"✅ Issue resolved - Type: {resolution_type}, Satisfaction: {customer_satisfaction}")
    return result, next_node

async def escalation_required(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle escalation requirements."""
    escalation_reason = args.get("escalation_reason", "complex_issue")
    department = args.get("department", "supervisor")
    notes = args.get("notes", "")
    
    escalation_data = {
        "reason": escalation_reason,
        "department": department,
        "notes": notes,
        "escalated_time": time.time()
    }
    
    flow_manager.state["escalation"] = escalation_data
    
    result = {
        "status": "success",
        "escalation_reason": escalation_reason,
        "department": department,
        "immediate_transfer": escalation_reason in ["angry_customer", "legal_issue", "emergency"]
    }
    
    if escalation_reason in ["angry_customer", "legal_issue", "emergency"]:
        next_node = create_immediate_transfer_node()
    else:
        next_node = create_escalation_preparation_node()
    
    logger.info(f"✅ Escalation required - Reason: {escalation_reason}, Department: {department}")
    return result, next_node

async def follow_up_scheduled(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle follow-up scheduling."""
    follow_up_type = args.get("follow_up_type", "standard")
    timeframe = args.get("timeframe", "24_hours")
    contact_method = args.get("contact_method", "phone")
    
    follow_up_data = {
        "type": follow_up_type,
        "timeframe": timeframe,
        "contact_method": contact_method,
        "scheduled_time": time.time()
    }
    
    flow_manager.state["follow_up"] = follow_up_data
    
    result = {
        "status": "success",
        "follow_up_type": follow_up_type,
        "timeframe": timeframe,
        "contact_method": contact_method
    }
    
    next_node = create_call_completion_node()
    
    logger.info(f"✅ Follow-up scheduled - Type: {follow_up_type}, Timeframe: {timeframe}")
    return result, next_node

async def emergency_handled(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle emergency situations."""
    emergency_type = args.get("emergency_type", "general")
    immediate_action = args.get("immediate_action", False)
    
    emergency_data = {
        "type": emergency_type,
        "immediate_action": immediate_action,
        "handled_time": time.time()
    }
    
    flow_manager.state["emergency"] = emergency_data
    
    result = {
        "status": "success",
        "emergency_type": emergency_type,
        "immediate_action": immediate_action
    }
    
    if immediate_action:
        next_node = create_immediate_transfer_node()
    else:
        next_node = create_emergency_resolution_node()
    
    logger.info(f"✅ Emergency handled - Type: {emergency_type}")
    return result, next_node

async def save_interaction_data(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Save complete interaction data."""
    interaction_summary = args.get("interaction_summary", "")
    satisfaction_rating = args.get("satisfaction_rating", "neutral")
    
    # Compile all interaction data
    interaction_data = {
        "timestamp": datetime.now().isoformat(),
        "call_duration": time.time() - flow_manager.state.get("call_start_time", time.time()),
        "customer_info": flow_manager.state.get("customer_info", {}),
        "call_type": flow_manager.state.get("call_type", "unknown"),
        "complaint": flow_manager.state.get("complaint"),
        "inquiry": flow_manager.state.get("inquiry"),
        "technical_issue": flow_manager.state.get("technical_issue"),
        "resolution": flow_manager.state.get("resolution"),
        "escalation": flow_manager.state.get("escalation"),
        "follow_up": flow_manager.state.get("follow_up"),
        "emergency": flow_manager.state.get("emergency"),
        "interaction_summary": interaction_summary,
        "satisfaction_rating": satisfaction_rating,
        "flow_state": dict(flow_manager.state)
    }
    
    # Save to JSON file
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        interactions_dir = os.path.join(project_root, "customer_interactions")
        os.makedirs(interactions_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        customer_name = interaction_data["customer_info"].get("customer_name", "unknown")
        safe_name = "".join(c for c in customer_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        
        filename = f"interaction_{safe_name}_{timestamp}.json"
        filepath = os.path.join(interactions_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(interaction_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Interaction data saved to: {filepath}")
        
    except Exception as e:
        logger.error(f"❌ Failed to save interaction data: {str(e)}")
        logger.exception("Full traceback:")
    
    flow_manager.state["interaction_saved"] = True
    
    result = {
        "status": "success",
        "interaction_summary": interaction_summary,
        "satisfaction_rating": satisfaction_rating,
        "data_saved": True
    }
    
    next_node = create_call_completion_node()
    
    logger.info(f"✅ Interaction data saved")
    return result, next_node

# Node creation functions for inbound customer service flow
def create_greeting_and_routing_node() -> NodeConfig:
    """Create the initial greeting and call routing node."""
    return NodeConfig(
        name="greeting_and_routing",
        task_messages=[
            {
                "role": "user",
                "content": """Greet the customer professionally and warmly. Introduce yourself as a customer service representative and ask how you can help them today. 

Listen carefully to understand their needs and determine the type of call:
- Complaint or issue to report
- Technical support needed
- Billing inquiry
- General information request
- Emergency situation

Also assess the urgency level based on their tone and situation.""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="call_routing",
                description="Route the call based on customer needs and urgency",
                properties={
                    "call_type": {
                        "type": "string",
                        "enum": ["complaint", "technical_support", "billing_inquiry", "general_inquiry", "emergency"]
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["low", "normal", "high", "critical"]
                    }
                },
                required=["call_type"],
                handler=call_routing,
            )
        ],
    )

def create_customer_info_collection_node() -> NodeConfig:
    """Create customer information collection node."""
    return NodeConfig(
        name="customer_info_collection",
        task_messages=[
            {
                "role": "user",
                "content": """To better assist you, I'll need to collect some information. Please provide:

1. Your account number (if applicable)
2. Your full name
3. Phone number on file
4. Email address (optional)

This helps me verify your account and provide personalized assistance.""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="customer_info_collected",
                description="Customer information has been collected",
                properties={
                    "account_number": {
                        "type": "string",
                        "description": "Customer's account number"
                    },
                    "customer_name": {
                        "type": "string",
                        "description": "Customer's full name"
                    },
                    "phone_number": {
                        "type": "string",
                        "description": "Customer's phone number"
                    },
                    "email": {
                        "type": "string",
                        "description": "Customer's email address"
                    }
                },
                required=["customer_name"],
                handler=customer_info_collected,
            )
        ],
    )

def create_complaint_handling_node() -> NodeConfig:
    """Create complaint handling node."""
    return NodeConfig(
        name="complaint_handling",
        task_messages=[
            {
                "role": "user",
                "content": """I understand you have a complaint or issue to report. I'm here to help resolve this for you.

Please tell me:
1. What specific issue are you experiencing?
2. When did this problem start?
3. How has this affected you?

I'll categorize your complaint and determine the best way to resolve it.""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="complaint_logged",
                description="Complaint has been documented",
                properties={
                    "complaint_category": {
                        "type": "string",
                        "enum": ["service_quality", "billing_error", "technical_issue", "staff_behavior", "service_outage", "other"]
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"]
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the complaint"
                    }
                },
                required=["complaint_category", "severity"],
                handler=complaint_logged,
            )
        ],
    )

def create_general_inquiry_node() -> NodeConfig:
    """Create general inquiry handling node."""
    return NodeConfig(
        name="general_inquiry",
        task_messages=[
            {
                "role": "user",
                "content": """I'd be happy to help with your inquiry. Please tell me what information you're looking for.

Common inquiries include:
- Business hours and locations
- Services offered
- Pricing information
- Account status
- General policies

What specific question can I answer for you?""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="inquiry_processed",
                description="Customer inquiry has been understood",
                properties={
                    "inquiry_type": {
                        "type": "string",
                        "enum": ["hours", "location", "services", "pricing", "account_status", "billing", "policies", "other"]
                    },
                    "specific_question": {
                        "type": "string",
                        "description": "The specific question asked"
                    }
                },
                required=["inquiry_type"],
                handler=inquiry_processed,
            )
        ],
    )

def create_technical_support_node() -> NodeConfig:
    """Create technical support node."""
    return NodeConfig(
        name="technical_support",
        task_messages=[
            {
                "role": "user",
                "content": """I'll help you with your technical issue. To better assist you, please provide:

1. What device or service are you having trouble with?
2. What exactly is happening? (error messages, symptoms)
3. When did this problem start?
4. Have you tried any troubleshooting steps already?

This will help me diagnose the issue and find the best solution.""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="technical_issue_diagnosed",
                description="Technical issue has been diagnosed",
                properties={
                    "issue_category": {
                        "type": "string",
                        "enum": ["password_reset", "account_settings", "app_issue", "connectivity", "hardware_failure", "network_outage", "other"]
                    },
                    "device_type": {
                        "type": "string",
                        "description": "Type of device experiencing issues"
                    },
                    "error_description": {
                        "type": "string",
                        "description": "Description of the error or problem"
                    }
                },
                required=["issue_category"],
                handler=technical_issue_diagnosed,
            )
        ],
    )

def create_billing_inquiry_node() -> NodeConfig:
    """Create billing inquiry node."""
    return NodeConfig(
        name="billing_inquiry",
        task_messages=[
            {
                "role": "user",
                "content": """I can help you with your billing question. Common billing inquiries include:

- Explaining charges on your bill
- Payment options and due dates
- Billing cycles and statements
- Account balance questions
- Payment history

What specific billing question do you have?""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="inquiry_processed",
                description="Billing inquiry processed",
                properties={
                    "inquiry_type": {
                        "type": "string",
                        "enum": ["bill_explanation", "payment_options", "account_balance", "payment_history", "billing_error", "other"]
                    },
                    "specific_question": {
                        "type": "string",
                        "description": "Specific billing question"
                    }
                },
                required=["inquiry_type"],
                handler=inquiry_processed,
            )
        ],
    )

def create_immediate_resolution_node() -> NodeConfig:
    """Create immediate resolution node."""
    return NodeConfig(
        name="immediate_resolution",
        task_messages=[
            {
                "role": "user",
                "content": """I can resolve this issue for you right now. Let me take care of this immediately.

[Provide the resolution steps or solution based on the issue type]

Is this resolution satisfactory? Do you have any other questions?""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="issue_resolved",
                description="Issue has been resolved successfully",
                properties={
                    "resolution_type": {
                        "type": "string",
                        "enum": ["immediate_fix", "account_adjustment", "service_reset", "information_provided"]
                    },
                    "customer_satisfaction": {
                        "type": "string",
                        "enum": ["very_satisfied", "satisfied", "neutral", "dissatisfied"]
                    },
                    "follow_up_needed": {
                        "type": "boolean",
                        "description": "Whether follow-up is needed"
                    }
                },
                required=["resolution_type", "customer_satisfaction"],
                handler=issue_resolved,
            )
        ],
    )

def create_complaint_resolution_node() -> NodeConfig:
    """Create complaint resolution node."""
    return NodeConfig(
        name="complaint_resolution",
        task_messages=[
            {
                "role": "user",
                "content": """I understand your frustration and I'm committed to resolving this complaint for you.

Here's what I can do to address your concern:
[Provide specific resolution steps based on complaint type]

I want to make sure you're completely satisfied with how we handle this. How does this resolution sound to you?""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="issue_resolved",
                description="Complaint has been resolved",
                properties={
                    "resolution_type": {
                        "type": "string",
                        "enum": ["policy_exception", "refund_credit", "service_improvement", "escalation_avoided"]
                    },
                    "customer_satisfaction": {
                        "type": "string",
                        "enum": ["very_satisfied", "satisfied", "neutral", "dissatisfied"]
                    },
                    "follow_up_needed": {
                        "type": "boolean"
                    }
                },
                required=["resolution_type", "customer_satisfaction"],
                handler=issue_resolved,
            ),
            FlowsFunctionSchema(
                name="escalation_required",
                description="Customer not satisfied, escalation needed",
                properties={
                    "escalation_reason": {
                        "type": "string",
                        "enum": ["unsatisfied_customer", "policy_limitation", "authorization_needed"]
                    },
                    "department": {
                        "type": "string",
                        "enum": ["supervisor", "billing_department", "technical_department", "management"]
                    },
                    "notes": {
                        "type": "string",
                        "description": "Notes for escalation"
                    }
                },
                required=["escalation_reason", "department"],
                handler=escalation_required,
            )
        ],
    )

def create_technical_resolution_node() -> NodeConfig:
    """Create technical resolution node."""
    return NodeConfig(
        name="technical_resolution",
        task_messages=[
            {
                "role": "user",
                "content": """I can help you resolve this technical issue. Let me walk you through the solution step by step:

[Provide specific technical resolution steps]

Please follow along and let me know if each step works for you. I'll make sure we get this completely resolved.""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="issue_resolved",
                description="Technical issue resolved successfully",
                properties={
                    "resolution_type": {
                        "type": "string",
                        "enum": ["guided_troubleshooting", "remote_fix", "account_reset", "configuration_change"]
                    },
                    "customer_satisfaction": {
                        "type": "string",
                        "enum": ["very_satisfied", "satisfied", "neutral", "dissatisfied"]
                    },
                    "follow_up_needed": {
                        "type": "boolean"
                    }
                },
                required=["resolution_type", "customer_satisfaction"],
                handler=issue_resolved,
            ),
            FlowsFunctionSchema(
                name="escalation_required",
                description="Issue requires technical escalation",
                properties={
                    "escalation_reason": {
                        "type": "string",
                        "enum": ["complex_technical_issue", "hardware_replacement_needed", "system_level_problem"]
                    },
                    "department": {
                        "type": "string",
                        "enum": ["technical_specialist", "field_service", "engineering"]
                    },
                    "notes": {
                        "type": "string"
                    }
                },
                required=["escalation_reason", "department"],
                handler=escalation_required,
            )
        ],
    )

def create_technical_troubleshooting_node() -> NodeConfig:
    """Create technical troubleshooting node."""
    return NodeConfig(
        name="technical_troubleshooting",
        task_messages=[
            {
                "role": "user",
                "content": """Let's troubleshoot this issue together. I'll guide you through some diagnostic steps to identify the problem.

First, let's try these basic troubleshooting steps:
[Provide troubleshooting steps based on issue type]

Please try these steps and let me know what happens.""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="issue_resolved",
                description="Troubleshooting successful, issue resolved",
                properties={
                    "resolution_type": {
                        "type": "string",
                        "enum": ["troubleshooting_successful", "setting_adjustment", "restart_fixed"]
                    },
                    "customer_satisfaction": {
                        "type": "string",
                        "enum": ["very_satisfied", "satisfied", "neutral", "dissatisfied"]
                    },
                    "follow_up_needed": {
                        "type": "boolean"
                    }
                },
                required=["resolution_type", "customer_satisfaction"],
                handler=issue_resolved,
            ),
            FlowsFunctionSchema(
                name="escalation_required",
                description="Troubleshooting unsuccessful, escalation needed",
                properties={
                    "escalation_reason": {
                        "type": "string",
                        "enum": ["troubleshooting_failed", "hardware_issue", "advanced_technical_support_needed"]
                    },
                    "department": {
                        "type": "string",
                        "enum": ["technical_specialist", "field_service", "level_2_support"]
                    },
                    "notes": {
                        "type": "string"
                    }
                },
                required=["escalation_reason", "department"],
                handler=escalation_required,
            )
        ],
    )

def create_information_provision_node() -> NodeConfig:
    """Create information provision node."""
    return NodeConfig(
        name="information_provision",
        task_messages=[
            {
                "role": "user",
                "content": """I'd be happy to provide that information for you.

[Provide the requested information based on inquiry type]

Is there anything else you'd like to know about our services or policies?""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="issue_resolved",
                description="Information provided successfully",
                properties={
                    "resolution_type": {
                        "type": "string",
                        "enum": ["information_provided", "question_answered", "clarification_given"]
                    },
                    "customer_satisfaction": {
                        "type": "string",
                        "enum": ["very_satisfied", "satisfied", "neutral", "dissatisfied"]
                    },
                    "follow_up_needed": {
                        "type": "boolean"
                    }
                },
                required=["resolution_type", "customer_satisfaction"],
                handler=issue_resolved,
            )
        ],
    )

def create_account_specific_inquiry_node() -> NodeConfig:
    """Create account-specific inquiry node."""
    return NodeConfig(
        name="account_specific_inquiry",
        task_messages=[
            {
                "role": "user",
                "content": """Let me look up your account information to answer your question.

[Provide account-specific information based on customer data]

I can see your account details here. Is this information helpful? Do you have any other account-related questions?""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="issue_resolved",
                description="Account inquiry resolved",
                properties={
                    "resolution_type": {
                        "type": "string",
                        "enum": ["account_info_provided", "status_explained", "history_reviewed"]
                    },
                    "customer_satisfaction": {
                        "type": "string",
                        "enum": ["very_satisfied", "satisfied", "neutral", "dissatisfied"]
                    },
                    "follow_up_needed": {
                        "type": "boolean"
                    }
                },
                required=["resolution_type", "customer_satisfaction"],
                handler=issue_resolved,
            )
        ],
    )

def create_escalation_node() -> NodeConfig:
    """Create escalation node."""
    return NodeConfig(
        name="escalation",
        task_messages=[
            {
                "role": "user",
                "content": """I understand this situation requires additional attention. Let me escalate this to the appropriate department for you.

I'm going to transfer you to [Department] who can provide specialized assistance with this matter. I'll make sure they have all the details of our conversation.

Is there anything else you'd like me to note before I transfer you?""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="escalation_required",
                description="Escalation details confirmed",
                properties={
                    "escalation_reason": {
                        "type": "string",
                        "enum": ["requires_specialist", "policy_exception_needed", "complex_issue", "customer_request"]
                    },
                    "department": {
                        "type": "string",
                        "enum": ["supervisor", "billing_specialist", "technical_specialist", "management", "legal"]
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional notes for the escalation"
                    }
                },
                required=["escalation_reason", "department"],
                handler=escalation_required,
            )
        ],
    )

def create_escalation_preparation_node() -> NodeConfig:
    """Create escalation preparation node."""
    return NodeConfig(
        name="escalation_preparation",
        task_messages=[
            {
                "role": "user",
                "content": """I'm preparing your case for escalation to ensure you get the best possible assistance.

Let me summarize what we've discussed and prepare a complete case file for the specialist. This will help them assist you more efficiently.

The specialist will contact you within [timeframe]. Is the phone number we have on file the best way to reach you?""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="follow_up_scheduled",
                description="Escalation follow-up scheduled",
                properties={
                    "follow_up_type": {
                        "type": "string",
                        "enum": ["specialist_callback", "department_transfer", "management_review"]
                    },
                    "timeframe": {
                        "type": "string",
                        "enum": ["within_hour", "same_day", "24_hours", "48_hours"]
                    },
                    "contact_method": {
                        "type": "string",
                        "enum": ["phone", "email", "both"]
                    }
                },
                required=["follow_up_type", "timeframe"],
                handler=follow_up_scheduled,
            )
        ],
    )

def create_immediate_transfer_node() -> NodeConfig:
    """Create immediate transfer node."""
    return NodeConfig(
        name="immediate_transfer",
        task_messages=[
            {
                "role": "user",
                "content": """I'm transferring you immediately to the appropriate department. Please hold while I connect you.

[Initiate immediate transfer to the designated department]

Thank you for holding. I'm connecting you now.""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="escalation_required",
                description="Immediate transfer completed",
                properties={
                    "escalation_reason": {
                        "type": "string",
                        "enum": ["emergency_transfer", "immediate_specialist_needed", "urgent_situation"]
                    },
                    "department": {
                        "type": "string",
                        "enum": ["emergency_services", "supervisor", "security", "management"]
                    },
                    "notes": {
                        "type": "string"
                    }
                },
                required=["escalation_reason", "department"],
                handler=escalation_required,
            )
        ],
    )

def create_emergency_handling_node() -> NodeConfig:
    """Create emergency handling node."""
    return NodeConfig(
        name="emergency_handling",
        task_messages=[
            {
                "role": "user",
                "content": """I understand this is an emergency situation. Let me help you immediately.

For life-threatening emergencies, please call 911.

For service emergencies, I can:
- Connect you to our emergency response team
- Escalate to management immediately
- Provide emergency contact information

What type of emergency assistance do you need?""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="emergency_handled",
                description="Emergency situation assessed",
                properties={
                    "emergency_type": {
                        "type": "string",
                        "enum": ["service_outage", "safety_concern", "security_issue", "urgent_technical", "other"]
                    },
                    "immediate_action": {
                        "type": "boolean",
                        "description": "Whether immediate action/transfer is required"
                    }
                },
                required=["emergency_type", "immediate_action"],
                handler=emergency_handled,
            )
        ],
    )

def create_emergency_resolution_node() -> NodeConfig:
    """Create emergency resolution node."""
    return NodeConfig(
        name="emergency_resolution",
        task_messages=[
            {
                "role": "user",
                "content": """I'm taking immediate action on your emergency situation.

[Provide emergency-specific resolution steps]

I've initiated the emergency protocol for your situation. You should receive immediate attention within the next few minutes.

Is there anything else urgent I can help you with right now?""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="issue_resolved",
                description="Emergency situation resolved",
                properties={
                    "resolution_type": {
                        "type": "string",
                        "enum": ["emergency_protocol_initiated", "immediate_service_restored", "emergency_contact_provided"]
                    },
                    "customer_satisfaction": {
                        "type": "string",
                        "enum": ["very_satisfied", "satisfied", "neutral", "dissatisfied"]
                    },
                    "follow_up_needed": {
                        "type": "boolean"
                    }
                },
                required=["resolution_type"],
                handler=issue_resolved,
            )
        ],
    )

def create_follow_up_scheduling_node() -> NodeConfig:
    """Create follow-up scheduling node."""
    return NodeConfig(
        name="follow_up_scheduling",
        task_messages=[
            {
                "role": "user",
                "content": """I'd like to schedule a follow-up to ensure everything continues to work well for you.

When would be a convenient time for us to check in with you?
- Within 24 hours
- In 2-3 days  
- Next week
- You'll contact us if needed

What's the best way to reach you for follow-up?""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="follow_up_scheduled",
                description="Follow-up has been scheduled",
                properties={
                    "follow_up_type": {
                        "type": "string",
                        "enum": ["satisfaction_check", "technical_verification", "service_confirmation", "proactive_support"]
                    },
                    "timeframe": {
                        "type": "string",
                        "enum": ["24_hours", "2_3_days", "one_week", "customer_initiated"]
                    },
                    "contact_method": {
                        "type": "string",
                        "enum": ["phone", "email", "text", "customer_preference"]
                    }
                },
                required=["follow_up_type", "timeframe"],
                handler=follow_up_scheduled,
            )
        ],
    )

def create_call_completion_node() -> NodeConfig:
    """Create call completion node."""
    return NodeConfig(
        name="call_completion",
        task_messages=[
            {
                "role": "user",
                "content": """Before we end our call, let me make sure I've addressed everything:

1. Have I completely resolved your [issue/question]?
2. Do you have any other questions or concerns?
3. Is there anything else I can help you with today?

Thank you for contacting us. We appreciate your business and hope you have a great day!

Please take a moment to rate your satisfaction with today's service if you'd like.""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="save_interaction_data",
                description="Save the complete interaction summary",
                properties={
                    "interaction_summary": {
                        "type": "string",
                        "description": "Brief summary of the interaction and resolution"
                    },
                    "satisfaction_rating": {
                        "type": "string",
                        "enum": ["very_satisfied", "satisfied", "neutral", "dissatisfied", "very_dissatisfied", "not_provided"]
                    }
                },
                required=["interaction_summary"],
                handler=save_interaction_data,
            )
        ],
    )

def get_inbound_flow_config() -> Dict[str, Any]:
    """Get the inbound customer service flow configuration."""
    return {
        "initial_node": "greeting_and_routing",
        "turn_manager": {
            "type": "basic",
            "timeout": 45
        },
        "nodes": {
            "greeting_and_routing": create_greeting_and_routing_node(),
            "customer_info_collection": create_customer_info_collection_node(),
            "complaint_handling": create_complaint_handling_node(),
            "general_inquiry": create_general_inquiry_node(),
            "technical_support": create_technical_support_node(),
            "billing_inquiry": create_billing_inquiry_node(),
            "immediate_resolution": create_immediate_resolution_node(),
            "complaint_resolution": create_complaint_resolution_node(),
            "technical_resolution": create_technical_resolution_node(),
            "technical_troubleshooting": create_technical_troubleshooting_node(),
            "information_provision": create_information_provision_node(),
            "account_specific_inquiry": create_account_specific_inquiry_node(),
            "escalation": create_escalation_node(),
            "escalation_preparation": create_escalation_preparation_node(),
            "immediate_transfer": create_immediate_transfer_node(),
            "emergency_handling": create_emergency_handling_node(),
            "emergency_resolution": create_emergency_resolution_node(),
            "follow_up_scheduling": create_follow_up_scheduling_node(),
            "call_completion": create_call_completion_node(),
        }
    }