import json
import logging
import asyncio
from typing import Dict, Any

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import get_object_or_404
from django.db import transaction
from asgiref.sync import sync_to_async

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from niva_app.models.dailycalls import DailyCall
from niva_app.models.course import Course
from niva_app.services.daily_service import DailyService

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class DailyWebhookView(View):
    """
    Handles Daily.co webhooks for events like room creation, 
    participant joining/leaving, recording start/stop
    """
    
    def post(self, request):
        """
        Process Daily.co webhook events
        """
        try:
            # Parse webhook payload
            payload = json.loads(request.body.decode('utf-8'))
            event_type = payload.get('type')
            event_data = payload.get('data', {})
            
            logger.info(f"Received Daily.co webhook: {event_type}")
            
            # Handle different event types
            if event_type == 'room.created':
                self._handle_room_created(event_data)
            elif event_type == 'participant.joined':
                self._handle_participant_joined(event_data)
            elif event_type == 'participant.left':
                self._handle_participant_left(event_data)
            elif event_type == 'recording.started':
                self._handle_recording_started(event_data)
            elif event_type == 'recording.stopped':
                self._handle_recording_stopped(event_data)
            elif event_type == 'recording.upload-completed':
                self._handle_recording_upload_completed(event_data)
            else:
                logger.warning(f"Unhandled webhook event type: {event_type}")
            
            return HttpResponse(status=200)
            
        except json.JSONDecodeError:
            logger.error("Invalid JSON payload in webhook")
            return HttpResponse(status=400)
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return HttpResponse(status=500)
    
    def _handle_room_created(self, data: Dict[str, Any]):
        """Handle room creation event"""
        room_name = data.get('room', {}).get('name')
        logger.info(f"Room created: {room_name}")
    
    def _handle_participant_joined(self, data: Dict[str, Any]):
        """Handle participant joined event"""
        room_name = data.get('room', {}).get('name')
        participant_id = data.get('participant', {}).get('user_id')
        logger.info(f"Participant {participant_id} joined room {room_name}")
    
    def _handle_participant_left(self, data: Dict[str, Any]):
        """Handle participant left event"""
        room_name = data.get('room', {}).get('name')
        participant_id = data.get('participant', {}).get('user_id')
        logger.info(f"Participant {participant_id} left room {room_name}")
    
    def _handle_recording_started(self, data: Dict[str, Any]):
        """Handle recording started event"""
        room_name = data.get('room', {}).get('name')
        recording_id = data.get('recording', {}).get('id')
        
        try:
            # Find the daily call by room name
            daily_call = DailyCall.objects.filter(daily_room_name=room_name).first()
            if daily_call:
                # Update call to indicate recording has started
                logger.info(f"Recording started for call {daily_call.call_sid}: {recording_id}")
        except Exception as e:
            logger.error(f"Error updating recording started: {str(e)}")
    
    def _handle_recording_stopped(self, data: Dict[str, Any]):
        """Handle recording stopped event"""
        room_name = data.get('room', {}).get('name')
        recording_id = data.get('recording', {}).get('id')
        logger.info(f"Recording stopped for room {room_name}: {recording_id}")
    
    def _handle_recording_upload_completed(self, data: Dict[str, Any]):
        """Handle recording upload completed event"""
        room_name = data.get('room', {}).get('name')
        recording_data = data.get('recording', {})
        recording_id = recording_data.get('id')
        download_url = recording_data.get('download_link')
        
        try:
            # Find the daily call by room name and update recording URL
            daily_call = DailyCall.objects.filter(daily_room_name=room_name).first()
            if daily_call and download_url:
                # Note: You may need to add a recording_url field if needed
                logger.info(f"Recording available for call {daily_call.call_sid}: {download_url}")
        except Exception as e:
            logger.error(f"Error updating recording URL: {str(e)}")


class DailyCallRecordingView(APIView):
    """
    Retrieves recording information for Daily calls
    """
    
    def get(self, request, daily_call_id):
        """
        Get recording information for a specific Daily call
        """
        return asyncio.run(self._async_get(request, daily_call_id))
    
    async def _async_get(self, request, daily_call_id):
        """
        Async implementation of get recording information
        """
        try:
            # Get the daily call using sync_to_async
            daily_call = await sync_to_async(get_object_or_404)(DailyCall, id=daily_call_id)
            
            # Initialize Daily service
            daily_service = DailyService()
            
            # Get recording information from Daily.co API
            recording_data = None
            if hasattr(daily_call, 'daily_room_name') and daily_call.daily_room_name:
                recording_data = await daily_service.get_recording_by_room_name(
                    daily_call.daily_room_name
                )
            
            # Close the service
            await daily_service.close()
            
            response_data = {
                'call_id': str(daily_call_id),
                'call_sid': daily_call.call_sid,
                'recording_data': recording_data,
                'course_id': str(daily_call.course.id) if daily_call.course else None,
                'course_name': daily_call.course.name if daily_call.course else None,
                'student_id': str(daily_call.student.id) if daily_call.student else None,
                'student_name': f"{daily_call.student.first_name} {daily_call.student.last_name}" if daily_call.student else None
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error retrieving recording: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve recording information'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DailyRoomAPIView(APIView):
    """
    Creates Daily.co rooms
    """
    
    def post(self, request):
        """
        Create a new Daily.co room - synchronous wrapper
        """
        return asyncio.run(self._async_post(request))
    
    async def _async_post(self, request):
        """
        Async implementation of create a new Daily.co room
        """
        try:
            data = request.data
            
            # Extract parameters from request
            room_name = data.get('room_name')
            privacy = data.get('privacy', 'private')
            exp_time = data.get('exp_time', 3600)
            enable_chat = data.get('enable_chat', False)
            enable_sip = data.get('enable_sip', True)
            sip_display_name = data.get('sip_display_name', 'SIP Participant')
            sip_video = data.get('sip_video', False)
            
            # Initialize Daily service
            daily_service = DailyService()
            
            # Create the room
            room_details = await daily_service.create_room(
                room_name=room_name,
                privacy=privacy,
                exp_time=exp_time,
                enable_chat=enable_chat,
                enable_sip=enable_sip,
                sip_display_name=sip_display_name,
                sip_video=sip_video
            )
            
            # Create room token
            token = await daily_service.create_room_token(
                room_details["name"], 
                expires_in=exp_time
            )
            
            # Close the service
            await daily_service.close()
            
            room_details["token"] = token
            
            return Response(room_details, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating room: {str(e)}")
            return Response(
                {'error': 'Failed to create room'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CreateAndSaveRoomAPIView(APIView):
    """
    Creates a Daily.co room and saves to database with course association
    """
    
    def post(self, request):
        """
        Create a Daily.co room and save call information to database - synchronous wrapper
        """
        return asyncio.run(self._async_post(request))
    
    async def _async_post(self, request):
        """
        Async implementation of create a Daily.co room and save call information to database
        """
        try:
            data = request.data
            
            # Extract required parameters - using course_id instead of course_id
            caller_phone_number = data.get('caller_phone_number')
            course_id = data.get('course_id')
            agent_id = data.get('agent_id')
            call_sid = data.get('call_sid')
            
            # Validate required fields
            if not all([caller_phone_number, course_id, agent_id, call_sid]):
                return Response(
                    {'error': 'Missing required fields: caller_phone_number, course_id, agent_id, call_sid'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate foreign key relationships using sync_to_async
            try:
                course = await sync_to_async(Course.objects.get)(id=course_id)
            except Course.DoesNotExist as e:
                return Response(
                    {'error': f'Invalid course reference: {str(e)}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Initialize Daily service
            daily_service = DailyService()
            
            # Create room and save to database - updated to use course_id instead of course_id
            room_and_call_details = await daily_service.create_and_save_room(
                caller_phone_number=caller_phone_number,
                course_id=course_id,
                agent_id=agent_id,
                call_sid=call_sid,
                user=request.user
            )
            
            # Close the service
            await daily_service.close()
            
            # Return the response from the service (already contains all data)
            response_data = {
                'success': True,
                'message': 'Room created and saved successfully',
                'daily_call_id': room_and_call_details["call"]["id"],
                'room': room_and_call_details["room"],
                'call': room_and_call_details["call"],
                'course_id': str(course_id),
                'course_name': course.name
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating and saving room: {str(e)}")
            return Response(
                {'error': f'Failed to create and save room: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )