import logging
import requests
from app import config
import json
from pydantic import BaseModel
import datetime
from typing import Optional, Dict, Any, Union
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
# from niva_app.lib.llm import gemini_client  # Commented out
from niva_app.lib.llm import groq_client  # Use Groq client instead
from niva_app.services.daily_service import DailyService
from niva_app.models.dailycalls import DailyCall
from niva_app.models.course import Course
from niva_app.models.students import Student
from niva_app.models.feedback import Feedback
from niva_app.models.agents import Agent
import base64
from django.db.utils import IntegrityError
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class AgentService:
    """
    Client service for communicating with the pipecat_agents microservice.
    """
    def __init__(self):
        # Use the correct config keys that match your settings
        self.base_url = config.PIPECAT_AGENTS_URL
        self.token = config.PIPECAT_BOT_API_TOKEN
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def handle_voice_call(self, phone_number, daily_call_id, daily_room_url, 
                         sip_endpoint, twilio_data, course_id, agent_id, student_id, token=None):
        """
        Forwards voice call requests to pipecat_agents service.
        
        Args:
            phone_number: Student's phone number
            daily_call_id: Daily.co call identifier
            daily_room_url: Daily.co room URL
            sip_endpoint: SIP endpoint for the call
            twilio_data: Twilio call data
            course_id: Course identifier (required)
            agent_id: Agent identifier (required)
            token: Daily.co authentication token (required)
            student_id: Student identifier (required)
        Returns:
            dict: Response from the pipecat_agents service
        """
        try:
            url = f"{self.base_url.rstrip('/')}/voice-call/"
            
            data = {
                "phone_number": phone_number,
                "daily_call_id": daily_call_id,
                "daily_room_url": daily_room_url,
                "sip_endpoint": sip_endpoint,
                "twilio_data": twilio_data,
                "course_id": course_id, 
                "agent_id": agent_id, 
                "student_id": student_id,   
                "token": token or "",      
            }
            
            logger.info(f"Sending voice call request to pipecat_agents: {daily_call_id}")
            
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Voice call request successful: {result}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with pipecat_agents service: {e}")
            return {
                "success": False,
                "error": f"Communication error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error in handle_voice_call: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def get_active_calls(self):
        """
        Get list of all active voice calls from pipecat_agents service.
        
        Returns:
            dict: Response containing active calls information
        """
        try:
            url = f"{self.base_url.rstrip('/')}/active-calls/"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting active calls: {e}")
            return {
                "success": False,
                "error": f"Communication error: {str(e)}"
            }
    
    def stop_voice_call(self, session_id):
        """
        Stop a specific voice call.
        
        Args:
            session_id: Session identifier for the call to stop
        
        Returns:
            dict: Response from the stop call endpoint
        """
        try:
            url = f"{self.base_url.rstrip('/')}/stop-call/"
            data = {"session_id": session_id}
            
            response = requests.post(url, headers=self.headers, json=data, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error stopping voice call {session_id}: {e}")
            return {
                "success": False,
                "error": f"Communication error: {str(e)}"
            }

    def health_check(self):
        """
        Checks if the pipecat_agents service is healthy.
        Returns:
            dict: Response from the health check endpoint
        """
        try:
            url = f"{self.base_url.rstrip('/')}/health/"
            
            # Health check is a public endpoint, no auth headers needed
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            result = response.json()
            logger.info("Pipecat agents health check successful")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

class Summary(BaseModel):
    summary: str

class Student_details(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    interest_level: Optional[str] = None
    timeline: Optional[str] = None
    notes: Optional[str] = None
    collected_at: Optional[str] = None

class InterviewFeedback(BaseModel):
    """Model for structured interview feedback from AI analysis"""
    overall_rating: int  # 1-10
    communication_rating: int  # 1-10
    technical_rating: int  # 1-10
    confidence_rating: int  # 1-10
    feedback_text: str
    strengths: str
    improvements: str
    recommendations: str

class AgentCallProcessor:
    """
    Service to handle post-call processing including data persistence
    """
    
    @staticmethod
    async def process_post_call_data(call_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for processing post-call data from pipecat_agents
        
        Args:
            call_data: Dictionary containing all call information
            
        Expected call_data structure:
        {
            "call_id": str,
            "session_id": str,
            "course_id": str,
            "caller_number": str,
            "agent_id": str,
            "transcript_content": str,
            "student_details": dict or None,
            "call_status": str,
            "student_id": str
        }
        
        Returns:
            Dict containing processing results
        """
        try:
            logger.info(f"Processing post-call data for call {call_data.get('call_id')}")
            
            # Extract data
            call_id = call_data.get("call_id")
            session_id = call_data.get("session_id")
            caller_number = call_data.get("caller_number")
            course_id = call_data.get("course_id")
            agent_id = call_data.get("agent_id")
            transcript_content = call_data.get("transcript_content")
            student_details = call_data.get("student_details")
            student_id = call_data.get("student_id")
            print("Student details from Agent: "+str(student_details))
            
            # Validate required fields
            if not all([call_id, session_id, course_id, agent_id, student_id]):
                raise ValueError("Missing required fields: call_id, session_id, course_id, agent_id")
            
            if student_details is None and transcript_content:
                logger.info("No student details provided, extracting from transcript")
                student_details = AgentCallProcessor.populate_student_details(transcript_content).dict()
            
            print("Fallback mechanism: "+str(student_details))

            # Generate call summary
            call_summary = ""
            try:
                call_summary = AgentCallProcessor.generate_call_summary(transcript_content)
                logger.info(f"Generated call summary: {call_summary[:100]}...")
            except Exception as e:
                logger.error(f"Error generating call summary: {e}")
            
            # Process student data if available
            if not student_id and student_details:
                logger.info(f"Processing student data: {student_details}")
                try:
                    student_id = await AgentCallProcessor.handle_student_data(
                        student_details, course_id
                    )
                    logger.info(f"Student processed - student_id: {student_id}")
                except Exception as e:
                    logger.error(f"Error handling student data: {e}")
            else:
                logger.info("No student details provided")
            
            # Save call data to database
            daily_call = None
            try:
                daily_call = await AgentCallProcessor.save_call_data_to_db(
                    call_id=call_id,
                    course_id=course_id,
                    agent_id=agent_id,
                    student_id=student_id,
                    transcript_content=transcript_content,
                    student_details=student_details,
                    call_summary=call_summary
                )
                if daily_call:
                    logger.info(f"Call data saved successfully with ID: {daily_call.id}")
                else:
                    logger.warning("Call data save returned None")
            except Exception as e:
                logger.error(f"Error saving call data to database: {e}")

            # Generate and save interview feedback if we have student and transcript
            feedback_created = False
            if daily_call and student_id and transcript_content:
                try:
                    feedback_created = await AgentCallProcessor.generate_and_save_feedback(
                        daily_call=daily_call,
                        student_id=student_id,
                        agent_id=agent_id,
                        course_id=course_id,
                        transcript_content=transcript_content
                    )
                    if feedback_created:
                        logger.info(f"Interview feedback generated and saved for call {call_id}")
                    else:
                        logger.warning(f"Failed to generate feedback for call {call_id}")
                except Exception as e:
                    logger.error(f"Error generating interview feedback: {e}")

            # Delete daily room
            try:
                if caller_number:
                    sanitized_phone = caller_number.replace("+", "").replace(" ", "").replace("-", "")
                    room_name = f"niva_{sanitized_phone}_{course_id}"
                    
                    daily_service = DailyService()
                    await daily_service.delete_room(room_name)
                else:
                    logger.warning("No caller_number provided, skipping room deletion")
            except Exception as e:
                logger.error(f"Error deleting Daily room: {e}")
            
            result = {
                "success": True,
                "call_id": call_id,
                "daily_call_id": daily_call.id if daily_call else None,
                "student_created": student_id is not None,
                "student_id": student_id,
                "feedback_created": feedback_created,
                "message": "Post-call data processed successfully"
            }
            
            logger.info(f"Successfully processed post-call data: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing post-call data: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to process post-call data"
            }

    @staticmethod
    async def generate_and_save_feedback(daily_call: DailyCall, student_id: str, 
                                       agent_id: str, course_id: str, 
                                       transcript_content: str) -> bool:
        """
        Generate interview feedback using AI analysis and save it to the database
        
        Args:
            daily_call: DailyCall instance
            student_id: Student ID
            agent_id: Agent ID  
            course_id: Course ID
            transcript_content: Interview transcript
            
        Returns:
            bool: True if feedback was successfully created
        """
        try:
            logger.info(f"Generating interview feedback for call {daily_call.call_sid}")
            
            # Get course information for context
            course_info = ""
            try:
                @sync_to_async
                def _get_course():
                    try:
                        return Course.objects.get(id=course_id)
                    except Course.DoesNotExist:
                        return None
                
                course = await _get_course()
                if course:
                    course_info = f"""
                    Course: {course.name}
                    Description: {course.description}
                    Evaluation Criteria: {course.evaluation_criteria or 'Standard interview assessment'}
                    Passing Score: {course.passing_score}/{course.max_score}
                    """
                else:
                    logger.warning(f"Course {course_id} not found, using generic assessment")
                    course_info = "Generic interview assessment"
            except Exception as e:
                logger.warning(f"Error getting course info: {e}, using generic assessment")
                course_info = "Generic interview assessment"

            # Generate AI feedback
            feedback_data = AgentCallProcessor.analyze_interview_transcript(
                transcript_content, course_info
            )
            
            if not feedback_data:
                logger.error("Failed to generate feedback data")
                return False

            # Save feedback to database
            @sync_to_async
            def _create_feedback():
                try:
                    # Check if feedback already exists for this call
                    existing_feedback = Feedback.objects.filter(daily_call=daily_call).first()
                    if existing_feedback:
                        logger.warning(f"Feedback already exists for call {daily_call.call_sid}, updating instead")
                        existing_feedback.student_id = student_id
                        existing_feedback.agent_id = agent_id
                        existing_feedback.overall_rating = feedback_data.overall_rating
                        existing_feedback.communication_rating = feedback_data.communication_rating
                        existing_feedback.technical_rating = feedback_data.technical_rating
                        existing_feedback.confidence_rating = feedback_data.confidence_rating
                        existing_feedback.feedback_text = feedback_data.feedback_text
                        existing_feedback.strengths = feedback_data.strengths
                        existing_feedback.improvements = feedback_data.improvements
                        existing_feedback.recommendations = feedback_data.recommendations
                        existing_feedback.save()
                        logger.info(f"Feedback updated with ID: {existing_feedback.id}")
                        return True
                    
                    with transaction.atomic():
                        feedback = Feedback.objects.create(
                            student_id=student_id,
                            daily_call=daily_call,
                            agent_id=agent_id,
                            overall_rating=feedback_data.overall_rating,
                            communication_rating=feedback_data.communication_rating,
                            technical_rating=feedback_data.technical_rating,
                            confidence_rating=feedback_data.confidence_rating,
                            feedback_text=feedback_data.feedback_text,
                            strengths=feedback_data.strengths,
                            improvements=feedback_data.improvements,
                            recommendations=feedback_data.recommendations
                        )
                        logger.info(f"Feedback created with ID: {feedback.id}")
                        return True
                except IntegrityError as e:
                    logger.error(f"Integrity error creating feedback (possibly duplicate): {e}")
                    return False
                except Exception as e:
                    logger.error(f"Database error creating feedback: {e}")
                    return False

            result = await _create_feedback()
            
            if result:
                logger.info(f"Successfully created interview feedback for student {student_id}")
            else:
                logger.error(f"Failed to save feedback to database")
                
            return result
            
        except Exception as e:
            logger.error(f"Error in generate_and_save_feedback: {e}")
            return False

    @staticmethod
    def analyze_interview_transcript(transcript_content: str, course_info: str = "") -> Optional[InterviewFeedback]:
        """
        Analyze interview transcript using AI and generate structured feedback
        
        Args:
            transcript_content: The interview transcript
            course_info: Information about the course/exam
            
        Returns:
            InterviewFeedback object with analysis results
        """
        if not transcript_content:
            logger.warning("No transcript content provided for analysis")
            return None

        try:
            prompt = f"""
            You are an expert interview assessor. Analyze the following interview transcript and provide comprehensive feedback.

            COURSE CONTEXT:
            {course_info}

            INTERVIEW TRANSCRIPT:
            {transcript_content}

            Please analyze the candidate's performance and provide ratings and feedback in the following format:

            RATING CRITERIA (Scale 1-10):
            - Overall Rating: Holistic assessment of interview performance
            - Communication Rating: Clarity, articulation, language skills, listening
            - Technical Rating: Subject knowledge, problem-solving, analytical thinking
            - Confidence Rating: Self-assurance, composure, handling of pressure

            FEEDBACK AREAS:
            - Feedback Text: Overall assessment summary (2-3 paragraphs)
            - Strengths: Specific areas where candidate performed well
            - Improvements: Areas that need development and enhancement
            - Recommendations: Specific actionable advice for growth

            ASSESSMENT GUIDELINES:
            - Be fair and constructive in your evaluation
            - Focus on both content and delivery
            - Consider the candidate's responses to different types of questions
            - Evaluate their thought process and reasoning ability
            - Assess their suitability for the role/course
            - Provide specific examples from the transcript when possible
            - Be encouraging while being honest about areas for improvement

            Return your analysis in JSON format with the specified fields.
            """

            # Commented out Gemini - using Groq instead
            # response = gemini_client.models.generate_content(
            #     model="gemini-2.5-pro",
            #     contents=[prompt],
            #     config={
            #         "response_mime_type": "application/json",
            #         "response_schema": InterviewFeedback,
            #     },
            # )
            # feedback_data = json.loads(response.text)
            
            # Use Groq for feedback generation
            schema_str = json.dumps(InterviewFeedback.model_json_schema(), indent=2)
            enhanced_prompt = f"{prompt}\n\nPlease respond in JSON format matching this schema:\n{schema_str}"
            
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": enhanced_prompt}],
                temperature=0.7,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )

            feedback_data = json.loads(response.choices[0].message.content)
            
            # Validate ratings are within range
            for rating_field in ['overall_rating', 'communication_rating', 'technical_rating', 'confidence_rating']:
                if rating_field in feedback_data:
                    rating = feedback_data[rating_field]
                    if not isinstance(rating, int) or rating < 1 or rating > 10:
                        logger.warning(f"Invalid {rating_field}: {rating}, setting to 5")
                        feedback_data[rating_field] = 5

            feedback = InterviewFeedback(**feedback_data)
            logger.info(f"Generated feedback - Overall: {feedback.overall_rating}/10")
            return feedback

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI feedback response: {e}")
            return None
        except Exception as e:
            logger.error(f"Error analyzing interview transcript: {e}")
            return None

    @staticmethod
    async def handle_student_data(student_details: dict, course_id: str) -> Optional[str]:
        """
        Handle student creation or update and return student_id
        """
        try:
            @sync_to_async
            def _process_student_data():
                with transaction.atomic():
                    # Parse student details
                    full_name = student_details.get("name", "").strip() if student_details.get("name") else ""
                    phone_number = student_details.get("phone_number", "").strip() if student_details.get("phone_number") else ""
                    email = student_details.get("email", "").strip() if student_details.get("email") else ""
                    
                    # Split name into first and last
                    name_parts = full_name.split(" ", 1)
                    first_name = name_parts[0] if name_parts else ""
                    last_name = name_parts[1] if len(name_parts) > 1 else ""
                    
                    # Clean and format phone number
                    if phone_number and not phone_number.startswith("+"):
                        phone_number = f"+{phone_number}"
                    
                    # Check if student already exists by phone number
                    student = None
                    if phone_number:
                        try:
                            student = Student.objects.get(phone_number=phone_number)
                            logger.info(f"Found existing student: {student.first_name} {student.last_name}")
                            
                            # Update existing student details
                            update_fields = []
                            if first_name and student.first_name != first_name:
                                student.first_name = first_name
                                update_fields.append('first_name')
                            if last_name and student.last_name != last_name:
                                student.last_name = last_name
                                update_fields.append('last_name')
                            if email and student.email != email:
                                student.email = email
                                update_fields.append('email')
                            
                            if update_fields:
                                student.save(update_fields=update_fields)
                                logger.info(f"Updated student fields: {', '.join(update_fields)}")
                                
                        except Student.DoesNotExist:
                            # Create new student
                            student = Student.objects.create(
                                first_name=first_name,
                                last_name=last_name,
                                phone_number=phone_number,
                                email=email,
                                gender="UNKNOWN"
                            )
                            logger.info(f"Created new student: {student.first_name} {student.last_name}")
                        
                        # Associate student with course if not already associated
                        try:
                            course = Course.objects.get(id=course_id)
                            if not student.course.filter(id=course_id).exists():
                                student.course.add(course)
                                logger.info(f"Associated student with course {course.name}")
                            else:
                                logger.info(f"Student already associated with course {course.name}")
                        except Course.DoesNotExist:
                            logger.error(f"Course with ID {course_id} not found")
                    
                    return student.id if student else None

            result = await _process_student_data()
            logger.info(f"Student data processing result: student_id={result}")
            return result
            
        except IntegrityError as e:
            logger.error(f"Database integrity error handling student data: {e}")
            return None
        except Exception as e:
            logger.error(f"Error handling student data: {e}")
            return None

    @staticmethod
    async def save_call_data_to_db(call_id: str, course_id: str, agent_id: str,
                                student_id: str = None,
                                transcript_content: str = None,
                                student_details: dict = None, 
                                call_summary: str = "") -> Optional[DailyCall]:
        """
        Save call data to the database
        """
        try:
            # Validate call_id length
            if len(call_id) > 255:  # Match your model's max_length
                logger.warning(f"Call ID too long ({len(call_id)} chars), hashing it")
                import hashlib
                call_id = hashlib.sha256(call_id.encode()).hexdigest()[:255]

            defaults = {
                'course_id': course_id,
                'agent_id': agent_id,
                'transcription': transcript_content or '',
                'call_summary': call_summary or '',
            }
            
            if student_id:
                defaults['student_id'] = student_id
            
            # Get or create the record
            daily_call, created = await DailyCall.objects.aget_or_create(
                call_sid=call_id,
                defaults=defaults
            )

            if not created:
                updates = {}
                if transcript_content:
                    updates['transcription'] = transcript_content
                if student_id:
                    updates['student_id'] = student_id
                if call_summary:
                    updates['call_summary'] = call_summary
                
                if updates:
                    for field, value in updates.items():
                        setattr(daily_call, field, value)
                    await daily_call.asave()

            logger.info(f"Call data saved for {call_id}")
            return daily_call

        except Exception as e:
            logger.error(f"Error saving call data: {e}\nCall ID: {call_id}\nLength: {len(call_id)}")
            return None
    
    @staticmethod
    def generate_call_summary(transcript_content: str, agent_name: str = "Agent") -> str:
        """
        Generate a call summary using Groq based on the transcript content.
        """
        if not transcript_content:
            return ""
        prompt = (
            f"Summarize the following call transcript in 2-3 sentences. "
            f"Summarize in this format in the first person: "
            f"`Hi there, this is {agent_name}. A student called for assistance with ... I will connect you to the student now.`\n"
            f"Transcript:\n"
            f"{transcript_content}\n\n"
            f"Respond in JSON format with a single field 'summary' containing your summary."
        )

        # Commented out Gemini - using Groq instead
        # response = gemini_client.models.generate_content(
        #     model="gemini-2.5-pro",
        #     contents=[prompt],
        #     config={
        #         "response_mime_type": "application/json",
        #         "response_schema": Summary,
        #     },
        # )
        
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=256,
                response_format={"type": "json_object"}
            )
            
            # Try to parse the summary from the response
            data = json.loads(response.choices[0].message.content)
            return data.get("summary", response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return f"Hi there, this is {agent_name}. A student contacted us. I will connect you to the student now."
    
    @staticmethod
    def populate_student_details(transcript_content: str, agent_name: str = "Agent") -> Student_details:
        """
        Populate student details from the transcript using Groq.
        Returns a Student_details object with extracted fields.
        """
        if not transcript_content:
            return Student_details()

        prompt = (
            "Extract the following student details from the call transcript:\n"
            "1. Name (if mentioned)\n"
            "2. Phone number (if mentioned)\n"
            "3. Email (if mentioned)\n"
            "4. Interest level (e.g., high, medium, low)\n"
            "5. Timeline (e.g., immediate, 1-3 months, etc.)\n"
            "6. Notes (any additional context)\n\n"
            "Return the details in JSON format with keys: name, phone_number, email, interest_level, timeline, notes.\n\n"
            f"Note: The agent's name is similar to human name, so don't use the same name under the name field. "
            "Also don't hallucinate and get random details - if you don't find anything, just leave them as null.\n\n"
            "Transcript:\n"
            f"{transcript_content}"
        )

        try:
            # Commented out Gemini - using Groq instead
            # response = gemini_client.models.generate_content(
            #     model="gemini-2.5-pro",
            #     contents=[prompt],
            #     config={
            #         "response_mime_type": "application/json",
            #         "response_schema": Student_details,
            #     },
            # )
            # return Student_details(**json.loads(response.text))
            
            # Use Groq for student details extraction
            schema_str = json.dumps(Student_details.model_json_schema(), indent=2)
            enhanced_prompt = f"{prompt}\n\nPlease respond in JSON format matching this schema:\n{schema_str}"
            
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": enhanced_prompt}],
                temperature=0.3,
                max_tokens=512,
                response_format={"type": "json_object"}
            )
            
            return Student_details(**json.loads(response.choices[0].message.content))
        except Exception as e:
            logger.error(f"Error extracting student details from transcript: {e}")
            return Student_details()