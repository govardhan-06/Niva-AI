from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from niva_app.services.pipecat_agent import AgentService
import uuid
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])  # Remove this in production
def test_voice_call(request):
    """
    Test endpoint to manually trigger a voice call to pipecat agents.
    """
    try:
        agent_service = AgentService()
        
        # Get data from request or use defaults
        data = request.data
        
        # Generate test data
        test_data = {
            "phone_number": data.get("phone_number", "+1234567890"),
            "daily_call_id": data.get("daily_call_id", f"test_call_{uuid.uuid4().hex[:8]}"),
            "daily_room_url": data.get("daily_room_url", "https://test.daily.co/test-room"),
            "sip_endpoint": data.get("sip_endpoint", "test@sip.example.com"),
            "course_id": data.get("course_id", "test_course_123"),
            "agent_id": data.get("agent_id", "test_agent_456"),
            "student_id": data.get("student_id", str(uuid.uuid4())),  # Add student_id parameter
            "token": data.get("token", "test_daily_token_123"),  # Add token parameter
            "twilio_data": data.get("twilio_data", {"test": True, "call_sid": "test_sid"})
        }
        
        logger.info(f"Testing voice call with data: {test_data}")
        
        # Call the pipecat agent service
        result = agent_service.handle_voice_call(**test_data)
        
        return Response({
            "success": True,
            "message": "Test voice call initiated",
            "request_data": test_data,
            "response": result
        })
        
    except Exception as e:
        logger.error(f"Test voice call failed: {e}")
        return Response({
            "success": False,
            "error": str(e)
        }, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def test_health_check(request):
    """
    Test endpoint to check pipecat agents health.
    """
    try:
        agent_service = AgentService()
        result = agent_service.health_check()
        
        return Response({
            "success": True,
            "health_check": result
        })
        
    except Exception as e:
        return Response({
            "success": False,
            "error": str(e)
        }, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def test_active_calls(request):
    """
    Test endpoint to get active calls from pipecat agents.
    """
    try:
        agent_service = AgentService()
        result = agent_service.get_active_calls()
        
        return Response({
            "success": True,
            "active_calls": result
        })
        
    except Exception as e:
        return Response({
            "success": False,
            "error": str(e)
        }, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def test_stop_call(request):
    """
    Test endpoint to stop a specific call.
    """
    try:
        session_id = request.data.get("session_id")
        if not session_id:
            return Response({
                "success": False,
                "error": "session_id is required"
            }, status=400)
        
        agent_service = AgentService()
        result = agent_service.stop_voice_call(session_id)
        
        return Response({
            "success": True,
            "stop_call_result": result
        })
        
    except Exception as e:
        return Response({
            "success": False,
            "error": str(e)
        }, status=500)