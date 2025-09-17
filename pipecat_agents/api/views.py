"""
Endpoints: 
● handle_voice_call: Processes voice call requests from nhapp 

Authentication: 
● Uses MicroserviceAuthentication for token-based authentication between services 
● Validates requests using the shared PIPECAT_BOT_API_TOKEN
"""
import asyncio
import logging
import json
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from pipecat_agents.pipecat_agent_runner import PipecatAgentRunner
from pipecat_agents.services.pipecat_agent_service import PipecatAgentService
from pipecat_agents.api.common import AuthenticatedAPIView, PublicAPIView

logger = logging.getLogger(__name__)

# Create service instance
pipecat_service = PipecatAgentService()

class HealthCheckView(PublicAPIView):
    """
    Test endpoint to verify Pipecat agent functionality.
    Public endpoint - no authentication required.
    """
    
    def get(self, request):
        try:    
            # Test both agent types
            outbound_runner = PipecatAgentRunner(agent_type="outbound")
            inbound_runner = PipecatAgentRunner(agent_type="inbound")
            
            # Test basic components for both
            for runner_type, runner in [("outbound", outbound_runner), ("inbound", inbound_runner)]:
                assert runner.registry is not None
                assert runner.flow_config is not None
                assert runner.transcript is not None
                assert runner.audiobuffer is not None
            
            return Response({
                "status": "healthy",
                "message": "Pipecat agents are functioning correctly",
                "agent_types": ["inbound", "outbound"],
                "components": {
                    "registry": "ok",
                    "flow_config": "ok", 
                    "transcript": "ok",
                    "audiobuffer": "ok"
                }
            })
            
        except Exception as e:
            logger.exception("Pipecat health check failed")
            return Response({
                "status": "unhealthy",
                "message": f"Pipecat health check failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class VoiceCallView(AuthenticatedAPIView):
    """
    Handle incoming voice call requests from niva_app.
    Uses the PipecatAgentService for processing.
    Requires microservice authentication.
    """
    
    def post(self, request):
        try:
            # Parse request data
            data = request.data if hasattr(request, 'data') else json.loads(request.body)
            
            # Extract parameters
            call_params = self._extract_call_parameters(data)
            
            # Validate required fields
            validation_error = self._validate_required_fields(call_params)
            if validation_error:
                return validation_error
            
            logger.info(f"Processing voice call for daily_call_id: {call_params['daily_call_id']}")
            
            # Handle the call asynchronously
            result = self._handle_voice_call_async(call_params)
            
            if result["success"]:
                return Response(result)
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON in request body")
            return Response({
                "success": False,
                "error": "Invalid JSON format"
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def _extract_call_parameters(self, data):
        """Extract and organize call parameters from request data"""
        return {
            'daily_call_id': data.get('daily_call_id'),
            'daily_room_url': data.get('daily_room_url'),
            'sip_endpoint': data.get('sip_endpoint'),
            'token': data.get('token', ''),  # Extract token from request
            'course_id': data.get('course_id'),
            'agent_id': data.get('agent_id'),
            'student_id': data.get('student_id'),
            'location_id': data.get('location_id', ''),
            'phone_number': data.get('phone_number', ''),
            'twilio_data': data.get('twilio_data', {})
        }
    
    def _validate_required_fields(self, params):
        """Validate that all required fields are present"""
        required_fields = ['daily_call_id', 'daily_room_url', 'sip_endpoint', 'course_id', 'agent_id', 'student_id']
        missing_fields = [field for field in required_fields if not params.get(field)]
        
        if missing_fields:
            return Response({
                "success": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return None
    
    def _handle_voice_call_async(self, params):
        """Handle the voice call asynchronously"""
        async def handle_call():
            return await pipecat_service.handle_voice_call(
                location_id=params['location_id'],
                phone_number=params['phone_number'],
                daily_call_id=params['daily_call_id'],
                daily_room_url=params['daily_room_url'],
                sip_endpoint=params['sip_endpoint'],
                twilio_data=params['twilio_data'],
                course_id=params['course_id'],
                agent_id=params['agent_id'],
                student_id=params['student_id'],
                token=params['token']  # Pass token to service
            )
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(handle_call())
        finally:
            loop.close()

class ActiveCallsView(AuthenticatedAPIView):
    """
    Get list of all active voice calls.
    Requires microservice authentication.
    """
    
    def get(self, request):
        try:
            active_processes = pipecat_service.get_active_processes()
            
            calls_info = []
            for session_id, process_info in active_processes.items():
                status_info = pipecat_service.get_process_status(session_id)
                if status_info:
                    calls_info.append(status_info)
            
            return Response({
                "success": True,
                "active_calls": len(calls_info),
                "calls": calls_info
            })
            
        except Exception as e:
            logger.exception(f"Error getting active calls: {e}")
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StopVoiceCallView(AuthenticatedAPIView):
    """
    Stop a specific voice call.
    Requires microservice authentication.
    """
    
    def post(self, request):
        try:
            data = request.data if hasattr(request, 'data') else json.loads(request.body)
            session_id = data.get('session_id')
            
            if not session_id:
                return Response({
                    "success": False,
                    "error": "Missing session_id"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            success = pipecat_service.stop_bot_process(session_id)
            
            return Response({
                "success": success,
                "message": f"Call {'stopped' if success else 'not found or failed to stop'}",
                "session_id": session_id
            })
            
        except Exception as e:
            logger.exception(f"Error stopping voice call: {e}")
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)