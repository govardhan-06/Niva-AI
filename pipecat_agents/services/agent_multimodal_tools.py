from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Outbound Sales Tools
collect_customer_details_function = FunctionSchema(
    name="collect_customer_details",
    description="Collect customer contact information when they show readiness to proceed or want to schedule follow-up. Always collect at least name and phone number.",
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
            "description": "Customer's email address (optional)"
        },
        "interest_level": {
            "type": "string",
            "enum": ["very_high", "high", "medium", "low"],
            "description": "Customer's level of interest based on the conversation"
        },
        "timeline": {
            "type": "string",
            "enum": ["immediate", "within_week", "within_month", "flexible"],
            "description": "Customer's timeline for implementation or purchase"
        },
        "notes": {
            "type": "string",
            "description": "Any special notes, requirements, or preferences mentioned by the customer"
        }
    },
    required=["name", "phone"]
)

schedule_callback_function = FunctionSchema(
    name="schedule_callback",
    description="Schedule a follow-up call when customer needs time to decide or wants to discuss with others. Use this when they're interested but not ready to proceed immediately.",
    properties={
        "callback_time": {
            "type": "string",
            "description": "When the customer wants to be called back (e.g., 'tomorrow afternoon', 'next week', 'in 3 days')"
        },
        "callback_reason": {
            "type": "string",
            "enum": ["think_it_over", "discuss_with_spouse", "financial_planning", "compare_options", "other"],
            "description": "Why they need the callback"
        },
        "interest_level": {
            "type": "string",
            "enum": ["high", "medium", "low"],
            "description": "Their current level of interest"
        },
        "preferred_time": {
            "type": "string",
            "description": "Their preferred time of day for the callback (e.g., 'morning', 'afternoon', 'evening')"
        },
        "contact_method": {
            "type": "string",
            "enum": ["phone", "email"],
            "description": "How they prefer to be contacted"
        },
        "notes": {
            "type": "string",
            "description": "Any specific notes or topics to cover in the callback"
        }
    },
    required=["callback_time", "interest_level"]
)

update_conversation_state_function = FunctionSchema(
    name="update_conversation_state",
    description="Update the current state of the conversation to track progress and customer engagement level. Use this periodically during the call.",
    properties={
        "current_stage": {
            "type": "string",
            "enum": ["rapport_building", "value_presentation", "needs_discovery", "objection_handling", "value_justification", "risk_reversal", "closing", "contact_collection"],
            "description": "Current stage of the sales conversation"
        },
        "customer_engagement": {
            "type": "string",
            "enum": ["very_engaged", "engaged", "neutral", "resistant", "disengaged"],
            "description": "Customer's current engagement level"
        },
        "primary_objection": {
            "type": "string",
            "description": "Main objection or concern expressed by the customer"
        },
        "needs_identified": {
            "type": "string",
            "description": "Key needs or pain points identified"
        },
        "next_action": {
            "type": "string",
            "description": "Recommended next action in the conversation flow"
        },
        "urgency_level": {
            "type": "string",
            "enum": ["immediate", "soon", "flexible", "unclear"],
            "description": "Customer's urgency level for their needs"
        }
    },
    required=["current_stage", "customer_engagement"]
)

end_conversation_function = FunctionSchema(
    name="end_conversation",
    description="End the conversation when it naturally concludes. Specify the outcome and any follow-up needs.",
    properties={
        "outcome": {
            "type": "string",
            "enum": ["sale_completed", "callback_scheduled", "follow_up_needed", "not_interested", "wrong_timing", "competitor_chosen"],
            "description": "The final outcome of the conversation"
        },
        "contact_collected": {
            "type": "boolean",
            "description": "Whether customer contact information was successfully collected"
        },
        "follow_up_required": {
            "type": "boolean",
            "description": "Whether any follow-up action is needed"
        },
        "follow_up_action": {
            "type": "string",
            "description": "Specific follow-up action required if any"
        },
        "customer_satisfaction": {
            "type": "string",
            "enum": ["very_satisfied", "satisfied", "neutral", "dissatisfied", "very_dissatisfied"],
            "description": "Customer's satisfaction level with the interaction"
        },
        "conversion_probability": {
            "type": "string",
            "enum": ["very_high", "high", "medium", "low", "very_low"],
            "description": "Probability of eventual conversion based on the conversation"
        },
        "summary": {
            "type": "string",
            "description": "Brief summary of the conversation and key outcomes"
        }
    },
    required=["outcome", "contact_collected", "follow_up_required"]
)

def get_outbound_sales_tools() -> ToolsSchema:
    """
    Get the tools schema for outbound sales conversations.
    
    Returns:
        ToolsSchema: Schema containing all outbound sales tools
    """
    return ToolsSchema(standard_tools=[
        collect_customer_details_function,
        schedule_callback_function,
        update_conversation_state_function,
        end_conversation_function
    ])

# Inbound Customer Service Tools
escalate_to_department_function = FunctionSchema(
    name="escalate_to_department",
    description="Escalate issues to supervisors, technical specialists, billing, or management when beyond your authority or expertise.",
    properties={
        "department": {
            "type": "string",
            "enum": ["supervisor", "technical_specialist", "billing", "management", "field_service"],
            "description": "Which department to escalate to"
        },
        "escalation_reason": {
            "type": "string",
            "enum": ["beyond_authority", "technical_complexity", "policy_exception", "customer_request", "legal_concern", "high_severity"],
            "description": "Reason for escalation"
        },
        "issue_summary": {
            "type": "string",
            "description": "Comprehensive summary of the issue for the receiving department"
        },
        "customer_impact": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"],
            "description": "Impact level on the customer"
        },
        "urgency": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"],
            "description": "Urgency of the escalation"
        },
        "resolution_attempts": {
            "type": "string",
            "description": "What resolution attempts have already been made"
        }
    },
    required=["department", "escalation_reason", "issue_summary"]
)

schedule_follow_up_function = FunctionSchema(
    name="schedule_follow_up",
    description="Schedule follow-up calls or callbacks for customers when resolution requires time or verification.",
    properties={
        "follow_up_type": {
            "type": "string",
            "enum": ["resolution_check", "service_verification", "satisfaction_survey", "proactive_support"],
            "description": "Type of follow-up needed"
        },
        "follow_up_date": {
            "type": "string",
            "description": "When the follow-up should occur"
        },
        "preferred_time": {
            "type": "string",
            "description": "Customer's preferred time for follow-up"
        },
        "contact_method": {
            "type": "string",
            "enum": ["phone", "email", "sms"],
            "description": "How to contact the customer"
        },
        "follow_up_notes": {
            "type": "string",
            "description": "Specific notes about what to cover in the follow-up"
        },
        "priority": {
            "type": "string",
            "enum": ["low", "medium", "high", "urgent"],
            "description": "Priority level of the follow-up"
        }
    },
    required=["follow_up_type", "follow_up_date"]
)

update_customer_info_function = FunctionSchema(
    name="update_customer_info",
    description="Update customer contact information or account details when they provide new information.",
    properties={
        "customer_id": {
            "type": "string",
            "description": "Customer's ID or account number"
        },
        "updated_phone": {
            "type": "string",
            "description": "New phone number if provided"
        },
        "updated_email": {
            "type": "string",
            "description": "New email address if provided"
        },
        "updated_address": {
            "type": "string",
            "description": "New address if provided"
        },
        "communication_preferences": {
            "type": "string",
            "description": "Customer's communication preferences"
        },
        "update_reason": {
            "type": "string",
            "description": "Reason for the information update"
        }
    },
    required=["customer_id"]
)

log_complaint_function = FunctionSchema(
    name="log_complaint",
    description="Formally log customer complaints with category, severity, and detailed description for tracking and resolution.",
    properties={
        "complaint_type": {
            "type": "string",
            "enum": ["service_quality", "billing_error", "technical_issue", "staff_behavior", "service_outage", "product_defect", "other"],
            "description": "Category of the complaint"
        },
        "severity": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"],
            "description": "Severity level of the complaint"
        },
        "complaint_description": {
            "type": "string",
            "description": "Detailed description of the complaint"
        },
        "customer_impact": {
            "type": "string",
            "description": "How this issue has impacted the customer"
        },
        "desired_resolution": {
            "type": "string",
            "description": "What resolution the customer is seeking"
        },
        "incident_date": {
            "type": "string",
            "description": "When the incident occurred"
        },
        "compensation_requested": {
            "type": "boolean",
            "description": "Whether customer is requesting compensation"
        }
    },
    required=["complaint_type", "severity", "complaint_description"]
)

create_service_ticket_function = FunctionSchema(
    name="create_service_ticket",
    description="Create technical support tickets for complex issues that require specialist attention or field service.",
    properties={
        "ticket_type": {
            "type": "string",
            "enum": ["password_reset", "account_settings", "app_issues", "connectivity", "hardware_failure", "network_outage", "installation", "maintenance"],
            "description": "Type of technical issue"
        },
        "priority": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"],
            "description": "Priority level of the ticket"
        },
        "issue_description": {
            "type": "string",
            "description": "Detailed description of the technical issue"
        },
        "symptoms": {
            "type": "string",
            "description": "Symptoms or error messages reported"
        },
        "troubleshooting_attempted": {
            "type": "string",
            "description": "Troubleshooting steps already attempted"
        },
        "customer_technical_level": {
            "type": "string",
            "enum": ["beginner", "intermediate", "advanced"],
            "description": "Customer's technical skill level"
        },
        "remote_access_possible": {
            "type": "boolean",
            "description": "Whether remote access is possible for resolution"
        },
        "field_service_needed": {
            "type": "boolean",
            "description": "Whether on-site service is required"
        }
    },
    required=["ticket_type", "priority", "issue_description"]
)

process_billing_inquiry_function = FunctionSchema(
    name="process_billing_inquiry",
    description="Handle billing-related questions and account balance inquiries. Verify customer identity before accessing account information.",
    properties={
        "inquiry_type": {
            "type": "string",
            "enum": ["balance_inquiry", "payment_history", "billing_dispute", "payment_arrangement", "service_charges", "refund_request"],
            "description": "Type of billing inquiry"
        },
        "account_verified": {
            "type": "boolean",
            "description": "Whether customer identity has been verified"
        },
        "verification_method": {
            "type": "string",
            "enum": ["account_number", "ssn_last_four", "security_question", "phone_verification"],
            "description": "How customer identity was verified"
        },
        "amount_in_question": {
            "type": "string",
            "description": "Specific amount being inquired about"
        },
        "billing_period": {
            "type": "string",
            "description": "Billing period in question"
        },
        "resolution_provided": {
            "type": "string",
            "description": "What resolution or information was provided"
        },
        "follow_up_needed": {
            "type": "boolean",
            "description": "Whether billing follow-up is needed"
        }
    },
    required=["inquiry_type", "account_verified"]
)

def get_inbound_customer_service_tools() -> ToolsSchema:
    """
    Get the tools schema for inbound customer service conversations.
    
    Returns:
        ToolsSchema: Schema containing all inbound customer service tools
    """
    return ToolsSchema(standard_tools=[
        escalate_to_department_function,
        schedule_follow_up_function,
        update_customer_info_function,
        log_complaint_function,
        create_service_ticket_function,
        process_billing_inquiry_function
    ])

def get_agent_tools(agent_type: str) -> ToolsSchema:
    """
    Get appropriate tools based on agent type.
    
    Args:
        agent_type: Type of agent ('outbound' or 'inbound')
    
    Returns:
        ToolsSchema: Appropriate tools for the agent type
    """
    if agent_type.lower() == 'outbound':
        return get_outbound_sales_tools()
    elif agent_type.lower() == 'inbound':
        return get_inbound_customer_service_tools()
    else:
        logger.warning(f"Unknown agent type: {agent_type}, defaulting to outbound tools")
        return get_outbound_sales_tools()