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

# Simplified result models
class InterviewDataResult(BaseModel):
    student_name: str
    topic_discussed: str
    response_quality: str
    notes: Optional[str] = None

class InterviewCompletionResult(BaseModel):
    overall_assessment: str
    key_observations: str
    interview_summary: str

# Simplified handler functions
async def interview_progress_tracked(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Track interview progress and responses naturally."""
    student_name = args.get("student_name", "Student")
    topic_discussed = args.get("topic_discussed", "")
    response_quality = args.get("response_quality", "good")
    notes = args.get("notes", "")
    
    # Store the interaction
    if "interview_data" not in flow_manager.state:
        flow_manager.state["interview_data"] = []
    
    flow_manager.state["interview_data"].append({
        "timestamp": time.time(),
        "student_name": student_name,
        "topic": topic_discussed,
        "quality": response_quality,
        "notes": notes
    })
    
    # Natural continuation - let the conversation flow
    result = {
        "status": "continue",
        "student_name": student_name,
        "topic_covered": topic_discussed
    }
    
    # Keep the same node to allow natural conversation flow
    next_node = create_natural_conversation_node()
    
    logger.info(f"✅ Interview progress tracked - Topic: {topic_discussed}")
    return result, next_node

async def interview_completed(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Complete the interview and save final assessment."""
    overall_assessment = args.get("overall_assessment", "positive")
    key_observations = args.get("key_observations", "")
    interview_summary = args.get("interview_summary", "")
    
    # Compile interview data
    interview_data = {
        "timestamp": datetime.now().isoformat(),
        "interview_duration": time.time() - flow_manager.state.get("start_time", time.time()),
        "interactions": flow_manager.state.get("interview_data", []),
        "final_assessment": {
            "overall_assessment": overall_assessment,
            "key_observations": key_observations,
            "summary": interview_summary
        },
        "flow_state": dict(flow_manager.state)
    }
    
    # Save interview data
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        interviews_dir = os.path.join(project_root, "interview_sessions")
        os.makedirs(interviews_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"interview_session_{timestamp}.json"
        filepath = os.path.join(interviews_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(interview_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Interview data saved to: {filepath}")
        
    except Exception as e:
        logger.error(f"❌ Failed to save interview data: {str(e)}")
    
    result = {
        "status": "completed",
        "assessment": overall_assessment,
        "summary": interview_summary
    }
    
    # End of flow
    next_node = None
    
    logger.info(f"✅ Interview completed with assessment: {overall_assessment}")
    return result, next_node

# Simplified node creation functions
def create_natural_conversation_node() -> NodeConfig:
    """Create a natural conversation node that allows free-flowing dialogue."""
    return NodeConfig(
        name="natural_conversation",
        task_messages=[
            {
                "role": "system",
                "content": """Continue the natural conversation as the INTERVIEWER.

CRITICAL ROLE CLARITY:
- You are the INTERVIEWER conducting the interview
- You are NOT the candidate/interviewee being interviewed
- You ask questions and the student answers
- Never respond as if someone is interviewing you
- Never answer questions as if you are the candidate

Your job as the interviewer:
- Ask follow-up questions based on what the student just said
- Explore different topics as they come up naturally
- Assess the student's knowledge and skills through casual discussion
- Share relevant information about the program or exam
- Move between topics smoothly based on the conversation flow

Be conversational, engaging, and let the interview develop organically. Don't follow a rigid script.

IMPORTANT: Most of the time, just respond naturally in conversation. Only use the tracking function occasionally when you notice something particularly noteworthy about the student's response. Don't track every single exchange.

If you feel you've gathered enough information or the student seems ready to wrap up, you can naturally conclude the interview.""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="interview_progress_tracked",
                description="OPTIONAL: Use sparingly to track particularly noteworthy responses or insights. Most responses don't need tracking - only use this when the student shares something especially interesting, insightful, or revealing about their knowledge/skills.",
                properties={
                    "student_name": {
                        "type": "string",
                        "description": "Student's name if mentioned"
                    },
                    "topic_discussed": {
                        "type": "string",
                        "description": "Main topic or subject area discussed"
                    },
                    "response_quality": {
                        "type": "string",
                        "enum": ["excellent", "good", "average", "needs_improvement"],
                        "description": "Quality of student's response"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Any notable observations or insights"
                    }
                },
                required=["topic_discussed"],
                handler=interview_progress_tracked,
            ),
            FlowsFunctionSchema(
                name="interview_completed",
                description="Use this to formally complete the interview when you've had a good conversation and feel ready to wrap up. This ends the session and generates the final assessment.",
                properties={
                    "overall_assessment": {
                        "type": "string",
                        "enum": ["excellent", "very_good", "good", "satisfactory", "needs_improvement"],
                        "description": "Overall assessment of the candidate"
                    },
                    "key_observations": {
                        "type": "string",
                        "description": "Key strengths and areas observed"
                    },
                    "interview_summary": {
                        "type": "string",
                        "description": "Brief summary of the interview discussion"
                    }
                },
                required=["overall_assessment", "key_observations"],
                handler=interview_completed,
            )
        ],
    )

def create_welcome_node() -> NodeConfig:
    """Create a welcoming, natural start to the interview."""
    return NodeConfig(
        name="welcome_start",
        task_messages=[
            {
                "role": "system",
                "content": """CRITICAL: You are the INTERVIEWER, not the interviewee. You ask questions and guide the conversation. Never act as if you are the candidate being interviewed.

You must speak first and initiate the conversation with a warm greeting.""",
            },
            {
                "role": "user",
                "content": """[The student has just joined the interview session. Start the interview now by greeting them warmly.]"""
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="interview_progress_tracked",
                description="OPTIONAL: Use only if the student shares something particularly interesting in their introduction. Most greetings don't need tracking.",
                properties={
                    "student_name": {
                        "type": "string",
                        "description": "Student's name if they introduce themselves"
                    },
                    "topic_discussed": {
                        "type": "string",
                        "description": "What the student chose to discuss first"
                    },
                    "response_quality": {
                        "type": "string",
                        "enum": ["excellent", "good", "average", "needs_improvement"],
                        "description": "How well the student engaged in the opening"
                    },
                    "notes": {
                        "type": "string",
                        "description": "First impressions and observations"
                    }
                },
                required=["topic_discussed"],
                handler=interview_progress_tracked,
            )
        ],
    )

def get_inbound_flow_config() -> Dict[str, Any]:
    """Get the natural interview flow configuration."""
    return {
        "initial_node": "welcome_start",
        "turn_manager": {
            "type": "basic",
        },
        "nodes": {
            "welcome_start": create_welcome_node(),
            "natural_conversation": create_natural_conversation_node(),
        }
    }