"""
Purpose: Manages interactions with the Daily.co API for creating and handling video/voice 
rooms.

Key Methods: 
● create_room(properties): Creates a new Daily.co room with SIP capabilities 
● delete_room(room_name): Deletes an existing Daily.co room 
● create_room_token(room_name, expires_in): Creates an authentication token for a room 
● create_and_save_room(caller_phone_number, course_id, agent_id, call_sid): Creates a room and saves it to the database as a DailyCall 
● get_call_recording(daily_call_id): Retrieves recording information 

Interfaces: 
● Interacts with Daily.co REST API 
● Creates and manages DailyCall model instances
"""
import time
import aiohttp, requests
import os
from typing import Dict, Any, Optional
from app.config import DAILY_API_KEY

from pipecat.transports.services.helpers.daily_rest import (
    DailyRESTHelper,
    DailyRoomParams,
    DailyRoomProperties,
    DailyRoomSipParams
)

from django.contrib.auth import get_user_model
from niva_app.models.dailycalls import DailyCall
from niva_app.models.course import Course
from niva_app.models.students import Student
from asgiref.sync import sync_to_async
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

class DailyService:
    def __init__(self, api_key: str = None, api_url: str = "https://api.daily.co/v1"):
        self.api_key = DAILY_API_KEY
        self.api_url = api_url
        self.session = None
        self.helper = None
    
    async def initialize(self):
        """Initialize the aiohttp session and Daily REST helper."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
            self.helper = DailyRESTHelper(
                daily_api_key=self.api_key,
                daily_api_url=self.api_url,
                aiohttp_session=self.session
            )
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def create_room(self, 
                         room_name: Optional[str] = None, 
                         privacy: str = "private",
                         exp_time: int = 3600,
                         enable_chat: bool = False,
                         enable_sip: bool = True,
                         sip_display_name: str = "SIP Participant",
                         sip_video: bool = False) -> Dict[str, Any]:
        """
        Creates a new Daily.co room with SIP capabilities.
        
        Args:
            room_name: Optional name for the room (if None, a random name will be generated)
            privacy: Room privacy setting ("private" or "public")
            exp_time: Room expiration time in seconds from now
            enable_chat: Whether to enable chat in the room
            enable_sip: Whether to enable SIP capabilities
            sip_display_name: Display name for SIP participants
            sip_video: Whether to enable video for SIP participants
            
        Returns:
            Dictionary containing room details
        """
        try:
            await self.initialize()
            
            # Configure SIP parameters if enabled
            sip_params = None
            if enable_sip:
                sip_params = DailyRoomSipParams(
                    display_name=sip_display_name,
                    video=sip_video,
                    sip_mode="dial-in",
                    num_endpoints=1
                )
            
            # Create room properties
            properties = DailyRoomProperties(
                exp=time.time() + exp_time,
                enable_chat=enable_chat,
                sip=sip_params,
                start_video_off=True
            )
            
            # Create room parameters
            params = DailyRoomParams(
                name=room_name,
                privacy=privacy,
                properties=properties
            )
            
            # Create the room
            room = await self.helper.create_room(params)
            
            # Return room details
            return {
                "id": room.id,
                "name": room.name,
                "url": room.url,
                "privacy": room.privacy,
                "created_at": room.created_at,
                "sip_endpoint": room.config.sip_endpoint if hasattr(room.config, "sip_endpoint") else None
            }
        
        except Exception as e:
            logger.error(f"Error creating room : {e}")
            raise e
            
        finally:
            await self.close()
    
    async def delete_room(self, room_name: str) -> bool:
        """
        Deletes an existing Daily.co room.
        
        Args:
            room_name: Name of the room to delete
            
        Returns:
            Boolean indicating success
        """
        try:
            await self.initialize()
            
            # Delete the room
            success = await self.helper.delete_room_by_name(room_name)
            return success
        
        finally:
            await self.close()
    
    async def create_room_token(self, room_name: str, expires_in: int = 3600, is_owner: bool = True) -> str:
        """
        Creates an authentication token for a room.
        
        Args:
            room_name: Name of the room
            expires_in: Token expiration time in seconds
            is_owner: Whether the token holder should have owner privileges
            
        Returns:
            Authentication token string
        """
        try:
            await self.initialize()
            
            # Create the token
            token = await self.helper.get_token(
                room_url=f"https://{room_name}.daily.co",
                expiry_time=expires_in,
                owner=is_owner
            )
            
            return token
        
        finally:
            await self.close()
    
    async def create_and_save_room(self, 
                          caller_phone_number: str, 
                          course_id: str, 
                          agent_id: str,
                          call_sid: str,
                          user=None) -> Dict[str, Any]:
        """
        Creates a room and saves it to the database as a DailyCall.
        
        Args:
            caller_phone_number: Phone number of the caller
            course_id: ID of the course
            agent_id: ID of the agent
            call_sid: Call SID
            user: Authenticated user (optional)
            
        Returns:
            Dictionary containing room and call details
        """
        sanitized_phone = caller_phone_number.replace("+", "").replace(" ", "").replace("-", "")
        
        room_name = f"niva_{sanitized_phone}_{course_id}"
        sip_display_name = f"niva_{sanitized_phone[-4:]}_{course_id}"

        room_details = await self.create_room(
            room_name=room_name,
            sip_display_name=sip_display_name,
            exp_time=3600  # 1 hour
        )
        
        # Generate a token for the room
        token = await self.create_room_token(room_details["name"], expires_in=7200)
        
        # Add token to room details
        room_details["token"] = token
        
        # Save to database
        @sync_to_async
        def create_daily_call_record():
            try:
                # Get course
                course = Course.objects.get(id=course_id)
                
                # Create a placeholder student or get existing one by phone number
                student, created = Student.objects.get_or_create(
                    phone_number=caller_phone_number,
                    defaults={
                        'first_name': 'Unknown',
                        'last_name': 'Student',
                        'email': '',
                        'gender': 'UNKNOWN'
                    }
                )
                
                # Associate student with course if not already associated
                if not student.course.filter(id=course_id).exists():
                    student.course.add(course)
                    logger.info(f"Associated student {student.phone_number} with course {course.name}")
                
                # Create DailyCall record
                with transaction.atomic():
                    daily_call = DailyCall.objects.create(
                        course=course,
                        student=student,
                        agent_id=agent_id,  # Store agent_id directly
                        call_sid=call_sid,
                        call_summary="",  
                        transcription=""
                    )
                
                logger.info(f"Created DailyCall record: {daily_call.id}")
                return daily_call
                
            except Course.DoesNotExist:
                logger.error(f"Course with ID {course_id} not found")
                raise ValueError(f"Course with ID {course_id} not found")
            except Exception as e:
                logger.error(f"Error saving DailyCall: {e}")
                raise e
        
        # Create the database record
        daily_call = await create_daily_call_record()

        # Return the combined room and call details
        return {
            "room": room_details,
            "call": {
                "id": str(daily_call.id),
                "caller_phone_number": caller_phone_number,
                "course_id": str(daily_call.course.id),
                "course_name": daily_call.course.name,
                "student_id": str(daily_call.student.id) if daily_call.student else None,
                "agent_id": agent_id,  # Use the passed agent_id directly
                "call_sid": call_sid,
                "daily_room_id": str(room_details["id"]), 
                "daily_room_name": room_details["name"],
                "daily_room_token": room_details["token"], 
                "status": "created",
                "created_at": room_details["created_at"]
            }
        }

    async def get_recording_by_room_name(self, room_name):
        """
        Retrieves recording information for a specific Daily room.
        
        Args:
            room_name (str): The name of the room for which to retrieve recordings
            
        Returns:
            dict: JSON response containing recording information
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        url = f"https://api.daily.co/v1/recordings?room_name={room_name}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error retrieving recording: {e}")
            return None
    
    async def get_recording_by_id(self, recording_id):
        """
        Retrieves information for a specific recording by ID.
        
        Args:
            recording_id (str): The ID of the recording to retrieve
            
        Returns:
            dict: JSON response containing recording information
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        url = f"https://api.daily.co/v1/recordings/{recording_id}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error retrieving recording: {e}")
            return None