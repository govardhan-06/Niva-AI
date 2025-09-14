import logging
import asyncio
import random
import uuid
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import serializers

from niva_app.services.daily_service import DailyService
from niva_app.services.pipecat_agent import AgentService
from niva_app.models.course import Course
from niva_app.models.agents import Agent
from app import config
from asgiref.sync import sync_to_async 

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class EntrypointVoiceAPI(APIView):
    """
    Entrypoint API for handling inbound calls.
    """
    
    class InputSerializer(serializers.Serializer):
        course_id = serializers.UUIDField()
        agent_id = serializers.UUIDField(required=False)
    
    def post(self, request, *args, **kwargs):
        """
        Handle Entrypoint for inbound calls.
        
        Expected parameters:
        - course_id: Course ID for the call
        - agent_id: Agent ID (optional, will use first active agent if not provided)
        """
        logger.info("Received EntrypointAPI for inbound call...")
        
        try:
            serializer = self.InputSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'success': False, 'error': 'Invalid input data', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            data = serializer.validated_data
            
            # Generate random Twilio data
            twilio_data = self._generate_random_twilio_data()
            
            course_id = str(data['course_id'])
            agent_id = str(data['agent_id']) if data.get('agent_id') else None
            
            # Process call asynchronously
            result = self._process_inbound_call_async(twilio_data, course_id, agent_id)
            return result
                
        except Exception as e:
            logger.exception(f"Error processing Twilio webhook: {e}")
            return Response(
                {'success': False, 'error': 'System error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_random_twilio_data(self):
        """Generate random Twilio data for testing."""
        return {
            'from': f"+1{random.randint(1000000000, 9999999999)}",  # Random US phone number
            'to': f"+91{random.randint(7000000000, 9999999999)}",  # Random Indian phone number
            'callsid': f"CA{uuid.uuid4().hex}",  # Random Call SID
            'accountsid': f"AC{uuid.uuid4().hex}",  # Random Account SID
            'callstatus': random.choice(["ringing", "in-progress", "completed"])  # Random call status
        }
    
    def _process_inbound_call_async(self, twilio_data, course_id, agent_id=None):
        """Process the inbound call asynchronously."""
        async def process_call():
            try:
                daily_service = DailyService()
                agent_service = AgentService()
                
                @sync_to_async
                def get_course_and_agent():
                    try:
                        # Get course
                        course = Course.objects.get(id=course_id, is_active=True)
                        
                        # Get agent - either provided or first active agent for the course
                        if agent_id:
                            agent = Agent.objects.get(id=agent_id, is_active=True)
                            # Verify agent is associated with the course
                            if not agent.courses.filter(id=course_id).exists():
                                raise ValueError(f"Agent {agent_id} is not associated with course {course_id}")
                        else:
                            # Get first active agent for this course
                            agent = course.agents.filter(is_active=True).first()
                            if not agent:
                                raise ValueError(f"No active agents found for course {course_id}")
                        
                        return course, agent
                        
                    except Course.DoesNotExist:
                        raise ValueError(f"Course {course_id} not found or is not active")
                    except Agent.DoesNotExist:
                        raise ValueError(f"Agent {agent_id} not found or is not active")
                
                # Get course and agent
                course, agent = await get_course_and_agent()
                
                # Create Daily room
                room_result = await daily_service.create_and_save_room(
                    caller_phone_number=twilio_data['from'],
                    course_id=course_id,
                    agent_id=str(agent.id),
                    call_sid=twilio_data['callsid']
                )
                
                # Extract room details
                daily_call_id = room_result['call']['id']  # Updated to use call id
                daily_room_url = room_result['room']['url']
                sip_endpoint = room_result['room'].get('sip_endpoint')
                daily_room_token = room_result["call"]["daily_room_token"]
                
                if not sip_endpoint:
                    logger.error("No SIP endpoint provided by Daily")
                    return Response(
                        {'success': False, 'error': 'No SIP endpoint provided by Daily'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Start pipecat agent
                agent_result = agent_service.handle_voice_call(
                    phone_number=twilio_data['from'],
                    daily_call_id=daily_call_id,
                    daily_room_url=daily_room_url,
                    sip_endpoint=sip_endpoint,
                    twilio_data=twilio_data,
                    course_id=course_id,
                    agent_id=str(agent.id),
                    token=daily_room_token,
                )
                
                return Response({
                    'success': True,
                    'sip_endpoint': sip_endpoint,
                    'daily_call_id': daily_call_id,
                    'agent_result': agent_result,
                    'room_url': daily_room_url,
                    'token': daily_room_token,
                    'course_name': course.name,
                    'agent_name': agent.name,
                })
                
            except ValueError as e:
                logger.error(f"Validation error: {e}")
                return Response(
                    {'success': False, 'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                logger.exception(f"Error in process_call: {e}")
                return Response(
                    {'success': False, 'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            finally:
                await daily_service.close()
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(process_call())
        finally:
            loop.close()
