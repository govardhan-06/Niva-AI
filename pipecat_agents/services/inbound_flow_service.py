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

# Result models for student interview flow
class StudentInfoResult(BaseModel):
    student_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    program_interest: str

class AcademicBackgroundResult(BaseModel):
    current_education_level: str
    institution: Optional[str] = None
    gpa: Optional[str] = None
    graduation_year: Optional[str] = None
    major: Optional[str] = None

class ProgramInterestResult(BaseModel):
    program_choice: str
    motivation: str
    career_goals: Optional[str] = None

class ExperienceResult(BaseModel):
    work_experience: Optional[str] = None
    projects: Optional[str] = None
    skills: Optional[str] = None
    achievements: Optional[str] = None

class BehavioralAssessmentResult(BaseModel):
    scenario_response: str
    problem_solving_approach: Optional[str] = None
    teamwork_example: Optional[str] = None

class InterviewSummaryResult(BaseModel):
    overall_impression: str
    strengths: str
    areas_for_improvement: Optional[str] = None
    recommendation: str

# Handler functions for student interview flow
async def interview_started(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Start the interview and collect basic information."""
    student_name = args.get("student_name")
    email = args.get("email")
    phone = args.get("phone")
    program_interest = args.get("program_interest")
    
    student_info = {
        "name": student_name,
        "email": email,
        "phone": phone,
        "program_interest": program_interest,
        "interview_start_time": time.time()
    }
    
    flow_manager.state["student_info"] = student_info
    
    result = {
        "status": "success",
        "student_name": student_name,
        "program_interest": program_interest
    }
    
    next_node = create_academic_background_node()
    
    logger.info(f"✅ Interview started for {student_name}, program: {program_interest}")
    return result, next_node

async def academic_background_collected(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle academic background information."""
    education_level = args.get("current_education_level")
    institution = args.get("institution")
    gpa = args.get("gpa")
    graduation_year = args.get("graduation_year")
    major = args.get("major")
    
    academic_data = {
        "education_level": education_level,
        "institution": institution,
        "gpa": gpa,
        "graduation_year": graduation_year,
        "major": major
    }
    
    flow_manager.state["academic_background"] = academic_data
    
    result = {
        "status": "success",
        "education_level": education_level,
        "strong_academic_record": gpa and float(gpa.replace("+", "")) >= 3.5 if gpa else False
    }
    
    next_node = create_program_interest_node()
    
    logger.info(f"✅ Academic background collected - Level: {education_level}")
    return result, next_node

async def program_interest_discussed(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle program interest and motivation discussion."""
    program_choice = args.get("program_choice")
    motivation = args.get("motivation")
    career_goals = args.get("career_goals")
    
    interest_data = {
        "program_choice": program_choice,
        "motivation": motivation,
        "career_goals": career_goals
    }
    
    flow_manager.state["program_interest"] = interest_data
    
    result = {
        "status": "success",
        "program_choice": program_choice,
        "clear_motivation": len(motivation) > 50 if motivation else False
    }
    
    next_node = create_experience_review_node()
    
    logger.info(f"✅ Program interest discussed - Choice: {program_choice}")
    return result, next_node

async def experience_reviewed(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle experience and skills review."""
    work_experience = args.get("work_experience")
    projects = args.get("projects")
    skills = args.get("skills")
    achievements = args.get("achievements")
    
    experience_data = {
        "work_experience": work_experience,
        "projects": projects,
        "skills": skills,
        "achievements": achievements
    }
    
    flow_manager.state["experience"] = experience_data
    
    result = {
        "status": "success",
        "has_relevant_experience": bool(work_experience or projects),
        "technical_skills": bool(skills)
    }
    
    next_node = create_behavioral_questions_node()
    
    logger.info(f"✅ Experience reviewed")
    return result, next_node

async def behavioral_assessment_completed(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle behavioral assessment responses."""
    scenario_response = args.get("scenario_response")
    problem_solving = args.get("problem_solving_approach")
    teamwork_example = args.get("teamwork_example")
    
    behavioral_data = {
        "scenario_response": scenario_response,
        "problem_solving": problem_solving,
        "teamwork_example": teamwork_example
    }
    
    flow_manager.state["behavioral_assessment"] = behavioral_data
    
    result = {
        "status": "success",
        "good_problem_solving": len(scenario_response) > 100 if scenario_response else False,
        "team_experience": bool(teamwork_example)
    }
    
    next_node = create_student_questions_node()
    
    logger.info(f"✅ Behavioral assessment completed")
    return result, next_node

async def student_questions_addressed(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Handle student's questions about the program."""
    questions_asked = args.get("questions_asked", "")
    questions_answered = args.get("questions_answered", True)
    
    qa_data = {
        "questions_asked": questions_asked,
        "questions_answered": questions_answered
    }
    
    flow_manager.state["student_questions"] = qa_data
    
    result = {
        "status": "success",
        "engaged_student": bool(questions_asked),
        "questions_answered": questions_answered
    }
    
    next_node = create_interview_completion_node()
    
    logger.info(f"✅ Student questions addressed")
    return result, next_node

async def save_interview_data(
    args: FlowArgs, 
    flow_manager: FlowManager
) -> Tuple[FlowResult, NodeConfig]:
    """Save complete interview data and assessment."""
    overall_impression = args.get("overall_impression", "positive")
    strengths = args.get("strengths", "")
    areas_for_improvement = args.get("areas_for_improvement", "")
    recommendation = args.get("recommendation", "consider")
    
    # Compile all interview data
    interview_data = {
        "timestamp": datetime.now().isoformat(),
        "interview_duration": time.time() - flow_manager.state.get("student_info", {}).get("interview_start_time", time.time()),
        "student_info": flow_manager.state.get("student_info", {}),
        "academic_background": flow_manager.state.get("academic_background", {}),
        "program_interest": flow_manager.state.get("program_interest", {}),
        "experience": flow_manager.state.get("experience", {}),
        "behavioral_assessment": flow_manager.state.get("behavioral_assessment", {}),
        "student_questions": flow_manager.state.get("student_questions", {}),
        "interviewer_assessment": {
            "overall_impression": overall_impression,
            "strengths": strengths,
            "areas_for_improvement": areas_for_improvement,
            "recommendation": recommendation
        },
        "flow_state": dict(flow_manager.state)
    }
    
    # Save to JSON file
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        interviews_dir = os.path.join(project_root, "student_interviews")
        os.makedirs(interviews_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        student_name = interview_data["student_info"].get("name", "unknown")
        safe_name = "".join(c for c in student_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        
        filename = f"interview_{safe_name}_{timestamp}.json"
        filepath = os.path.join(interviews_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(interview_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Interview data saved to: {filepath}")
        
    except Exception as e:
        logger.error(f"❌ Failed to save interview data: {str(e)}")
        logger.exception("Full traceback:")
    
    flow_manager.state["interview_saved"] = True
    
    result = {
        "status": "success",
        "overall_impression": overall_impression,
        "recommendation": recommendation,
        "data_saved": True
    }
    
    next_node = None  # End of flow
    
    logger.info(f"✅ Interview completed and data saved")
    return result, next_node

# Node creation functions for student interview flow
def create_welcome_and_intro_node() -> NodeConfig:
    """Create the initial welcome and introduction node."""
    return NodeConfig(
        name="welcome_and_intro",
        task_messages=[
            {
                "role": "user",
                "content": """Hello! Welcome to your admissions interview. I'm excited to learn more about you and your interest in our programs.

This interview will take about 30-45 minutes. We'll discuss your background, academic experience, and goals. Feel free to ask questions throughout our conversation.

Let's start with some basic information:
- What's your full name?
- What's your email address?
- Phone number?
- Which program are you most interested in?""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="interview_started",
                description="Basic student information collected",
                properties={
                    "student_name": {
                        "type": "string",
                        "description": "Student's full name"
                    },
                    "email": {
                        "type": "string",
                        "description": "Student's email address"
                    },
                    "phone": {
                        "type": "string",
                        "description": "Student's phone number"
                    },
                    "program_interest": {
                        "type": "string",
                        "description": "Program the student is interested in"
                    }
                },
                required=["student_name", "program_interest"],
                handler=interview_started,
            )
        ],
    )

def create_academic_background_node() -> NodeConfig:
    """Create academic background collection node."""
    return NodeConfig(
        name="academic_background",
        task_messages=[
            {
                "role": "user",
                "content": """Great! Now let's talk about your academic background.

Please tell me about:
1. What's your current education level? (high school, undergraduate, graduate, etc.)
2. Which school/institution are you currently at or did you graduate from?
3. What's your GPA or academic standing?
4. When do you graduate or when did you graduate?
5. What's your major or area of study?""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="academic_background_collected",
                description="Academic background information collected",
                properties={
                    "current_education_level": {
                        "type": "string",
                        "enum": ["high_school", "undergraduate", "graduate", "postgraduate", "working_professional"]
                    },
                    "institution": {
                        "type": "string",
                        "description": "Name of current or previous institution"
                    },
                    "gpa": {
                        "type": "string",
                        "description": "GPA or academic standing"
                    },
                    "graduation_year": {
                        "type": "string",
                        "description": "Expected or actual graduation year"
                    },
                    "major": {
                        "type": "string",
                        "description": "Major or field of study"
                    }
                },
                required=["current_education_level"],
                handler=academic_background_collected,
            )
        ],
    )

def create_program_interest_node() -> NodeConfig:
    """Create program interest discussion node."""
    return NodeConfig(
        name="program_interest",
        task_messages=[
            {
                "role": "user",
                "content": """Now I'd like to understand your interest in our program better.

Please tell me:
1. Why are you specifically interested in this program?
2. What motivated you to apply?
3. What are your career goals after completing this program?
4. How does this program align with your long-term objectives?

Take your time to give me a thoughtful response.""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="program_interest_discussed",
                description="Program interest and motivation discussed",
                properties={
                    "program_choice": {
                        "type": "string",
                        "description": "Specific program the student chose"
                    },
                    "motivation": {
                        "type": "string",
                        "description": "Why the student is interested in this program"
                    },
                    "career_goals": {
                        "type": "string",
                        "description": "Student's career goals and aspirations"
                    }
                },
                required=["program_choice", "motivation"],
                handler=program_interest_discussed,
            )
        ],
    )

def create_experience_review_node() -> NodeConfig:
    """Create experience and skills review node."""
    return NodeConfig(
        name="experience_review",
        task_messages=[
            {
                "role": "user",
                "content": """Let's talk about your experience and skills.

Please share:
1. Any work experience you have (internships, part-time jobs, full-time work)
2. Projects you've worked on (academic, personal, or professional)
3. Technical or other relevant skills you've developed
4. Any achievements or accomplishments you're proud of

Don't worry if you don't have extensive experience - we value potential and enthusiasm too!""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="experience_reviewed",
                description="Experience and skills information collected",
                properties={
                    "work_experience": {
                        "type": "string",
                        "description": "Student's work experience"
                    },
                    "projects": {
                        "type": "string",
                        "description": "Projects the student has worked on"
                    },
                    "skills": {
                        "type": "string",
                        "description": "Technical and other relevant skills"
                    },
                    "achievements": {
                        "type": "string",
                        "description": "Notable achievements or accomplishments"
                    }
                },
                required=[],
                handler=experience_reviewed,
            )
        ],
    )

def create_behavioral_questions_node() -> NodeConfig:
    """Create behavioral questions node."""
    return NodeConfig(
        name="behavioral_questions",
        task_messages=[
            {
                "role": "user",
                "content": """Now I'd like to ask you some scenario-based questions to understand how you approach challenges.

Here's a situation: "Imagine you're working on a team project with a tight deadline, but one team member isn't contributing their fair share. How would you handle this situation?"

Also, please tell me:
1. Describe your approach to solving complex problems
2. Give me an example of a time you worked effectively in a team

Take your time to think through your responses.""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="behavioral_assessment_completed",
                description="Behavioral questions answered",
                properties={
                    "scenario_response": {
                        "type": "string",
                        "description": "Response to the team scenario question"
                    },
                    "problem_solving_approach": {
                        "type": "string",
                        "description": "How the student approaches problem-solving"
                    },
                    "teamwork_example": {
                        "type": "string",
                        "description": "Example of effective teamwork"
                    }
                },
                required=["scenario_response"],
                handler=behavioral_assessment_completed,
            )
        ],
    )

def create_student_questions_node() -> NodeConfig:
    """Create student questions node."""
    return NodeConfig(
        name="student_questions",
        task_messages=[
            {
                "role": "user",
                "content": """Now it's your turn! Do you have any questions about:
- The program curriculum or structure
- Faculty and research opportunities
- Student life and campus resources
- Career services and job placement
- Application process and timeline
- Anything else about the program or institution

I'm here to help clarify anything you'd like to know.""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="student_questions_addressed",
                description="Student's questions have been addressed",
                properties={
                    "questions_asked": {
                        "type": "string",
                        "description": "Questions the student asked"
                    },
                    "questions_answered": {
                        "type": "boolean",
                        "description": "Whether the questions were satisfactorily answered"
                    }
                },
                required=["questions_answered"],
                handler=student_questions_addressed,
            )
        ],
    )

def create_interview_completion_node() -> NodeConfig:
    """Create interview completion and assessment node."""
    return NodeConfig(
        name="interview_completion",
        task_messages=[
            {
                "role": "user",
                "content": """Thank you for taking the time to interview with us today. You've shared some great insights about yourself and your goals.

Before we wrap up, let me provide you with next steps:
- We'll review your application and interview
- You should hear back from us within [timeframe]
- Feel free to reach out if you have additional questions

Based on our conversation today, I'd like to complete my assessment of the interview. Thank you again for your time!""",
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="save_interview_data",
                description="Complete interview assessment and save data",
                properties={
                    "overall_impression": {
                        "type": "string",
                        "enum": ["excellent", "very_good", "good", "fair", "needs_improvement"]
                    },
                    "strengths": {
                        "type": "string",
                        "description": "Key strengths observed during the interview"
                    },
                    "areas_for_improvement": {
                        "type": "string",
                        "description": "Areas where the student could improve"
                    },
                    "recommendation": {
                        "type": "string",
                        "enum": ["strong_recommend", "recommend", "consider", "do_not_recommend"]
                    }
                },
                required=["overall_impression", "strengths", "recommendation"],
                handler=save_interview_data,
            )
        ],
    )

def get_inbound_flow_config() -> Dict[str, Any]:
    """Get the student interview flow configuration."""
    return {
        "initial_node": "welcome_and_intro",
        "turn_manager": {
            "type": "basic",
            "timeout": 60
        },
        "nodes": {
            "welcome_and_intro": create_welcome_and_intro_node(),
            "academic_background": create_academic_background_node(),
            "program_interest": create_program_interest_node(),
            "experience_review": create_experience_review_node(),
            "behavioral_questions": create_behavioral_questions_node(),
            "student_questions": create_student_questions_node(),
            "interview_completion": create_interview_completion_node(),
        }
    }