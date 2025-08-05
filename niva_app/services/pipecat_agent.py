import logging
import requests
from app import config
import json
from pydantic import BaseModel
import datetime
from typing import Optional, Dict, Any, Union
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from custard_app.lib.llm import gemini_client
from custard_app.services.storage import StorageService
from custard_app.services.daily_service import DailyService
from custard_app.models.dailycalls import DailyCall
from custard_app.models.company import Company
from custard_app.models.customer import Customer
from custard_app.models.phonenumber import PhoneNumber
from app.config import GCS_BUCKET_NAME, GCS_BASE_URL
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
        self.token = config.PIPECAT_BOT_TOKEN
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def handle_voice_call(self, phone_number, daily_call_id, daily_room_url, 
                         sip_endpoint, twilio_data, company_id, agent_id, token=None):
        """
        Forwards voice call requests to pipecat_agents service.
        
        Args:
            phone_number: Customer's phone number
            daily_call_id: Daily.co call identifier
            daily_room_url: Daily.co room URL
            sip_endpoint: SIP endpoint for the call
            twilio_data: Twilio call data
            company_id: Company identifier (required)
            agent_id: Agent identifier (required)
            token: Daily.co authentication token (required)
        
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
                "company_id": company_id, 
                "agent_id": agent_id,    
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

class Customer_details(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    interest_level: Optional[str] = None
    timeline: Optional[str] = None
    notes: Optional[str] = None
    collected_at: Optional[str] = None

class AgentCallProcessor:
    """
    Service to handle post-call processing including recording upload and data persistence
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
            "company_id": str,
            "caller_number": str,
            "agent_id": str,
            "transcript_content": str,
            "recording_file_data": bytes or None,
            "customer_details": dict or None,
            "call_status": str
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
            company_id = call_data.get("company_id")
            agent_id = call_data.get("agent_id")
            transcript_content = call_data.get("transcript_content")
            recording_file_data = call_data.get("recording_file_data")
            customer_details = call_data.get("customer_details")

            call_summary = AgentCallProcessor.generate_call_summary(transcript_content)

            print("Customer details from Agent: "+str(customer_details))
            
            # Validate required fields
            if not all([call_id, session_id, company_id, agent_id]):
                raise ValueError("Missing required fields: call_id, session_id, company_id, agent_id")
            
            if customer_details is None and transcript_content:
                logger.info("No customer details provided, extracting from transcript")
                customer_details = AgentCallProcessor.populate_customer_details(transcript_content).dict()
            
            print("Fallback mechanism: "+str(customer_details))

            # Generate call summary first
            call_summary = ""
            try:
                call_summary = AgentCallProcessor.generate_call_summary(transcript_content)
                logger.info(f"Generated call summary: {call_summary[:100]}...")
            except Exception as e:
                logger.error(f"Error generating call summary: {e}")
            
            # Process recording upload if available
            recording_url = None
            if recording_file_data:
                try:
                    recording_url = await AgentCallProcessor.handle_recording_upload(
                        recording_file_data, call_id, session_id
                    )
                    if recording_url:
                        logger.info(f"Recording uploaded successfully: {recording_url}")
                    else:
                        logger.warning("Recording upload returned None")
                except Exception as e:
                    logger.error(f"Error handling recording upload: {e}")
            else:
                logger.info("No recording data provided")
            
            # Process customer data if available
            customer_id = None
            phone_number_id = None
            if customer_details:
                logger.info(f"Processing customer data: {customer_details}")
                try:
                    customer_id, phone_number_id = await AgentCallProcessor.handle_customer_data(
                        customer_details, company_id
                    )
                    logger.info(f"Customer processed - customer_id: {customer_id}, phone_number_id: {phone_number_id}")
                except Exception as e:
                    logger.error(f"Error handling customer data: {e}")
            else:
                logger.info("No customer details provided")
            
            # Save call data to database
            daily_call = None
            try:
                daily_call = await AgentCallProcessor.save_call_data_to_db(
                    call_id=call_id,
                    company_id=company_id,
                    agent_id=agent_id,
                    customer_id=customer_id,
                    phone_number_id=phone_number_id,
                    recording_url=recording_url,
                    transcript_content=transcript_content,
                    customer_details=customer_details,
                    call_summary=call_summary
                )
                if daily_call:
                    logger.info(f"Call data saved successfully with ID: {daily_call.id}")
                else:
                    logger.warning("Call data save returned None")
            except Exception as e:
                logger.error(f"Error saving call data to database: {e}")

            # Delete daily room
            try:
                if caller_number:
                    sanitized_phone = caller_number.replace("+", "").replace(" ", "").replace("-", "")
                    room_name = f"qulander_{sanitized_phone}_{company_id}"
                    
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
                "recording_url": recording_url,
                "customer_created": customer_id is not None,
                "customer_id": customer_id,
                "phone_number_id": phone_number_id,
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
    async def handle_recording_upload(recording_file_data: Union[bytes, str], call_id: str, session_id: str) -> Optional[str]:
        """
        Handle recording upload from binary data or base64 string
        """
        try:
            # Check if recording already exists
            existing_url = await AgentCallProcessor.check_if_recording_exists_in_gcp(call_id, session_id)
            if existing_url:
                logger.info(f"Recording already exists, returning existing URL: {existing_url}")
                return existing_url
            
            # Convert string input to bytes if needed
            if isinstance(recording_file_data, str):
                try:
                    recording_file_data = base64.b64decode(recording_file_data)
                    logger.info("Successfully decoded base64 recording data")
                except Exception as e:
                    logger.error(f"Failed to decode base64 recording data: {e}")
                    return None
            
            # Validate we have binary data at this point
            if not isinstance(recording_file_data, bytes):
                logger.error("Invalid recording data format - expected bytes or base64 string")
                return None
            
            # Create temporary file
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                temp_file.write(recording_file_data)
                temp_file_path = temp_file.name
            
            try:
                # Upload to GCP
                recording_url = await AgentCallProcessor.upload_recording_to_gcp(
                    temp_file_path, call_id, session_id
                )
                return recording_url
            finally:
                # Clean up temp file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Error handling recording upload: {e}")
            return None
    
    @staticmethod
    async def upload_recording_to_gcp(recording_file_path: str, call_id: str, session_id: str) -> Optional[str]:
        """
        Upload the recording to GCP Storage and return the URL.
        """
        try:
            bucket_name = GCS_BUCKET_NAME
            if not bucket_name:
                logger.error("GCS_BUCKET_NAME not configured")
                return None

            # Generate blob path with timestamp for uniqueness
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            blob_path = f"call_recordings/{call_id}_{session_id}_{timestamp}.wav"

            # Upload the file to GCP Storage
            logger.info(f"Uploading recording to GCP: {blob_path}")
            
            # Make the upload operation async-safe
            upload_func = sync_to_async(StorageService.upload_blob)
            success = await upload_func(
                bucket_name=bucket_name,
                source_file_name=recording_file_path,
                destination_blob_name=blob_path
            )

            if success:
                # Generate public URL
                recording_url = f"{GCS_BASE_URL}/{bucket_name}/{blob_path}"
                logger.info(f"Successfully uploaded recording: {recording_url}")
                return recording_url
            else:
                logger.error(f"Failed to upload recording for call {call_id}")
                return None

        except Exception as e:
            logger.error(f"Error uploading recording to GCP Storage: {str(e)}")
            return None

    @staticmethod
    async def check_if_recording_exists_in_gcp(call_id: str, session_id: str) -> Optional[str]:
        """
        Check if a recording file already exists in GCP Storage for the given call and session.
        """
        try:
            bucket_name = GCS_BUCKET_NAME
            if not bucket_name:
                logger.error("GCS_BUCKET_NAME not configured")
                return None
    
            def _check_blobs():
                client = StorageService.get_client()
                bucket = client.bucket(bucket_name)
                prefix = f"call_recordings/{call_id}_{session_id}_"
                blobs = list(bucket.list_blobs(prefix=prefix))
                
                for blob in blobs:
                    if blob.name.endswith('.wav') or blob.name.endswith('.mp3'):
                        recording_url = f"{GCS_BASE_URL}/{bucket_name}/{blob.name}"
                        return recording_url
                return None
            
            check_blobs_async = sync_to_async(_check_blobs)
            result = await check_blobs_async()
            
            if result:
                logger.info(f"Found existing recording: {result}")
            else:
                logger.info(f"No existing recording found for call {call_id}, session {session_id}")
            
            return result

        except Exception as e:
            logger.error(f"Error checking if recording exists in GCP Storage: {str(e)}")
            return None

    @staticmethod
    async def handle_customer_data(customer_details: dict, company_id: str) -> tuple[Optional[str], Optional[str]]:
        """
        Handle customer creation or update and return customer_id and phone_number_id
        """
        try:
            @sync_to_async
            def _process_customer_data():
                with transaction.atomic():
                    # Parse customer details
                    full_name = customer_details.get("name", "").strip() if customer_details.get("name") else ""
                    phone = customer_details.get("phone", "").strip() if customer_details.get("phone") else ""
                    email = customer_details.get("email", "").strip() if customer_details.get("email") else ""
                    
                    # Split name into first and last
                    name_parts = full_name.split(" ", 1)
                    first_name = name_parts[0] if name_parts else ""
                    last_name = name_parts[1] if len(name_parts) > 1 else ""
                    
                    # Clean and format phone number
                    if phone and not phone.startswith("+"):
                        phone = f"+{phone}"
                    
                    # Check if customer already exists by phone number
                    customer = None
                    if phone:
                        try:
                            customer = Customer.objects.get(phone_number=phone)
                            logger.info(f"Found existing customer: {customer.first_name} {customer.last_name}")
                            
                            # Update existing customer details
                            update_fields = []
                            if first_name and customer.first_name != first_name:
                                customer.first_name = first_name
                                update_fields.append('first_name')
                            if last_name and customer.last_name != last_name:
                                customer.last_name = last_name
                                update_fields.append('last_name')
                            if email and customer.email != email:
                                customer.email = email
                                update_fields.append('email')
                            
                            if update_fields:
                                customer.save(update_fields=update_fields)
                                logger.info(f"Updated customer fields: {', '.join(update_fields)}")
                                
                        except Customer.DoesNotExist:
                            # Create new customer
                            customer = Customer.objects.create(
                                first_name=first_name,
                                last_name=last_name,
                                phone_number=phone,
                                email=email,
                                gender="UNKNOWN"
                            )
                            logger.info(f"Created new customer: {customer.first_name} {customer.last_name}")
                        
                        # Associate customer with company if not already associated
                        try:
                            company = Company.objects.get(id=company_id)
                            if not customer.companies.filter(id=company_id).exists():
                                customer.companies.add(company)
                                logger.info(f"Associated customer with company {company.name}")
                        except Company.DoesNotExist:
                            logger.error(f"Company with ID {company_id} not found")
                    
                    # Handle phone number lookup
                    phone_number = None
                    if phone:
                        try:
                            phone_number = PhoneNumber.objects.get(phone_number=phone)
                        except PhoneNumber.DoesNotExist:
                            logger.info(f"Phone number {phone} not found in PhoneNumber table")
                    
                    return (customer.id if customer else None, 
                        phone_number.id if phone_number else None)

            result = await _process_customer_data()
            logger.info(f"Customer data processing result: customer_id={result[0]}, phone_number_id={result[1]}")
            return result
            
        except IntegrityError as e:
            logger.error(f"Database integrity error handling customer data: {e}")
            return None, None
        except Exception as e:
            logger.error(f"Error handling customer data: {e}")
            return None, None

    @staticmethod
    async def save_call_data_to_db(call_id: str, company_id: str, agent_id: str,
                                 customer_id: str = None, phone_number_id: str = None,
                                 recording_url: str = None, transcript_content: str = None,
                                 customer_details: dict = None, call_summary: str = "") -> Optional[DailyCall]:
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
                'company_id': company_id,
                'agent_id': agent_id,
                'recording_url': recording_url or '',
                'transcription': transcript_content or '',
                'call_summary': call_summary or '',
                'needs_staff_followup': False,
                'staff_message': customer_details
            }
            
            if customer_id:
                defaults['customer_id'] = customer_id
            if phone_number_id:
                defaults['phone_number_id'] = phone_number_id
            
            # Get or create the record
            daily_call, created = await DailyCall.objects.aget_or_create(
                call_sid=call_id,
                defaults=defaults
            )

            if not created:
                updates = {}
                if recording_url:
                    updates['recording_url'] = recording_url
                if transcript_content:
                    updates['transcription'] = transcript_content
                if customer_id:
                    updates['customer_id'] = customer_id
                if phone_number_id:
                    updates['phone_number_id'] = phone_number_id
                if customer_details:
                    updates['staff_message'] = customer_details
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
        Generate a call summary using Gemini based on the transcript content.
        """
        if not transcript_content:
            return ""
        prompt = (
            f"Summarize the following call transcript in 2-3 sentences. "
            f"Summarize in this format in the first person: "
            f"`Hi there, this is {agent_name}. A caller needs assistance with ... I will connect you to the caller now.`\n"
            f"Transcript:\n"
            f"{transcript_content}"
        )

        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config={
                "response_mime_type": "application/json",
                "response_schema": Summary,
            },
        )
        try:
            # Try to parse the summary from the response
            data = json.loads(response.text)
            return data.get("summary", response.text)
        except Exception:
            return response.text
    
    @staticmethod
    def populate_customer_details(transcript_content: str, agent_name: str = "Agent") -> Customer_details:
        """
        Populate customer details from the transcript using Gemini.
        Returns a Customer_details object with extracted fields.
        """
        if not transcript_content:
            return Customer_details()

        prompt = (
            "Extract the following customer details from the call transcript:\n"
            "1. Name (if mentioned)\n"
            "2. Phone number (if mentioned)\n"
            "3. Email (if mentioned)\n"
            "4. Interest level (e.g., high, medium, low)\n"
            "5. Timeline (e.g., immediate, 1-3 months, etc.)\n"
            "6. Notes (any additional context)\n\n"
            "Return the details in JSON format with keys: name, phone, email, interest_level, timeline, notes.\n\n"
            f"Note: The agent's name is similar to human name, so don't use the same name under the name field. "
            "Also don't hallucinate and get random details - if you don't find anything, just leave them as null.\n\n"
            "Transcript:\n"
            f"{transcript_content}"
        )

        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt],
                config={
                    "response_mime_type": "application/json",
                    "response_schema": Customer_details,
                },
            )
            return Customer_details(**json.loads(response.text))
        except Exception as e:
            logger.error(f"Error extracting customer details from transcript: {e}")
            return Customer_details()