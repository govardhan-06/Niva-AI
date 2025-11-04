import asyncio
import logging
import subprocess
import threading
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import json

from pipecat.transports.services.daily import DailyTransport
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

@dataclass
class AgentService:
    transport: DailyTransport
    pipeline: Pipeline
    task: PipelineTask
    context: dict

class AgentServiceRegistry:
    _instance = None
    _active_services: Dict[str, AgentService] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentServiceRegistry, cls).__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, session_id: str, agent_service: AgentService) -> AgentService:
        """Register an agent service instance for the current session."""
        cls._active_services[session_id] = agent_service
        return agent_service

    @classmethod
    def get(cls, session_id: str) -> Optional[AgentService]:
        """Get the agent service instance for the current session."""
        return cls._active_services.get(session_id)

    @classmethod
    def remove(cls, session_id: str) -> None:
        """Remove an agent service instance for the session."""
        if session_id in cls._active_services:
            del cls._active_services[session_id]

    @classmethod
    def get_all_active_sessions(cls) -> Dict[str, AgentService]:
        """Get all active agent service instances."""
        return cls._active_services

class PipecatAgentService:
    """
    Core service for handling voice interactions using Pipecat AI.
    """
    
    def __init__(self):
        self.registry = AgentServiceRegistry()
        self.active_processes = {}  # Track running bot processes
    
    async def handle_voice_call(
        self, 
        location_id: str, 
        phone_number: str, 
        daily_call_id: str, 
        daily_room_url: str,
        sip_endpoint: str, 
        twilio_data: dict = None,
        course_id: str = None,
        agent_id: str = None,
        student_id: str = None,
        token: str = None  
    ) -> dict:
        """
        Processes incoming voice calls using the pipecat_agent_runner.
        
        Args:
            location_id: Identifier for the call location
            phone_number: Customer's phone number
            daily_call_id: Daily.co call identifier
            daily_room_url: Daily.co room URL
            sip_endpoint: SIP endpoint for the call
            twilio_data: Additional Twilio call data
            course_id: course identifier
            agent_id: Agent identifier
            student_id: Student identifier
            token: Daily.co authentication token
        
        Returns:
            dict: Response containing success status and call details
        """
        try:
            logger.info(f"Handling voice call for daily_call_id: {daily_call_id}")
            
            # Validate required parameters
            if not all([daily_call_id, daily_room_url, sip_endpoint]):
                raise ValueError("Missing required parameters: daily_call_id, daily_room_url, or sip_endpoint")
            
            # Start the bot process
            bot_process_info = await self._start_bot_process(
                daily_call_id=daily_call_id,
                room_url=daily_room_url,
                sip_endpoint=sip_endpoint,
                course_id=course_id,
                agent_id=agent_id,
                phone_number=phone_number,
                location_id=location_id,
                twilio_data=twilio_data,
                student_id=student_id,
                token=token or "" 
            )
            
            logger.info(f"Voice call processing started successfully for call {daily_call_id}")
            
            return {
                "success": True,
                "message": "Voice call processing started",
                "call_id": daily_call_id,
                "session_id": bot_process_info["session_id"],
                "process_id": bot_process_info["process_id"],
            }
            
        except Exception as e:
            logger.error(f"Error handling voice call {daily_call_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "call_id": daily_call_id
            }
    
    async def _start_bot_process(
        self,
        daily_call_id: str,
        room_url: str,
        sip_endpoint: str = None,
        course_id: str = None,
        agent_id: str = None,
        phone_number: str = None,
        location_id: str = None,
        twilio_data: dict = None,
        student_id: str = None,
        token: str = ""
    ) -> dict:
        """
        Starts the agent process for voice calls.
        
        Args:
            daily_call_id: Daily.co call identifier
            room_url: Daily.co room URL
            sip_endpoint: SIP endpoint for the call
            course_id: course identifier
            agent_id: Agent identifier
            phone_number: Customer's phone number
            location_id: Location identifier
            twilio_data: Additional Twilio data
            student_id: Student identifier
            token: Authentication token
        
        Returns:
            dict: Process information including session_id and process_id
        """
        try:
            # Import here to avoid circular import
            from pipecat_agents.pipecat_agent_runner import PipecatAgentRunner
            
            session_id = f"session_{daily_call_id}"
            
            # Determine agent type
            agent_name = await self._get_agent_name(course_id, agent_id)
            
            logger.info(f"Starting bot process for session: {session_id}")
            
            # Create runner instance
            runner = PipecatAgentRunner()
            
            # Prepare context data
            context_data = {
                "call_id": daily_call_id,
                "room_url": room_url,
                "sip_endpoint": sip_endpoint,
                "phone_number": phone_number,
                "location_id": location_id,
                "course_id": course_id,
                "agent_id": agent_id,
                "agent_name": agent_name,
                "twilio_data": twilio_data or {},
                "student_id": student_id,
            }
            
            # Start the agent in a separate thread to avoid asyncio loop issues
            def run_agent_task():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    logger.info(f"Starting inbound agent {agent_name} for call {daily_call_id}")
                    loop.run_until_complete(
                        runner.run_inbound_agent(
                            room_url=room_url,
                            token=token,
                            call_id=daily_call_id,
                            sip_uri=sip_endpoint,
                            session_id=session_id,
                            course_id=course_id,
                            agent_id=agent_id,
                            caller_number=phone_number,
                            student_id=student_id,
                        )
                    )
                except Exception as e:
                    logger.error(f"Error in agent task for session {daily_call_id}: {e}")
                    logger.exception("Full traceback:")
                finally:
                    # Clean up process tracking
                    if session_id in self.active_processes:
                        del self.active_processes[session_id]
                    loop.close()
            
            # Start the thread
            thread = threading.Thread(target=run_agent_task, name=f"agent-{session_id}")
            thread.daemon = True
            thread.start()
            
            # Track the process
            process_info = {
                "session_id": session_id,
                "process_id": thread.ident,
                "thread": thread,
                "agent_name": agent_name,
                "context": context_data,
                "started_at": asyncio.get_event_loop().time()
            }
            
            self.active_processes[session_id] = process_info
            
            logger.info(f"Bot process started successfully: {process_info}")
            
            return process_info
            
        except Exception as e:
            logger.error(f"Failed to start bot process for call {daily_call_id}: {e}")
            raise
    
    async def _get_agent_name(self, course_id: str, agent_id: str) -> Tuple[str, str]:
        """
        Determine agent name.
        """
        @sync_to_async
        def _get_agent_sync():
            # Lazy import to avoid Django initialization issues
            from niva_app.models.agents import Agent
            try:
                agent = Agent.objects.filter(id=agent_id, courses__id=course_id, is_active=True).first()
                if agent:
                    return agent.name
                else:
                    logger.warning(f"Agent with id {agent_id} not found for course {course_id}")
                    return "Unknown Agent"
            except Exception as e:
                logger.error(f"Error determining agent type: {e}")
                return "Unknown Agent"

        return await _get_agent_sync()
    
    def get_active_processes(self) -> Dict[str, dict]:
        """
        Get all currently active bot processes.
        
        Returns:
            Dict[str, dict]: Dictionary of active processes keyed by session_id
        """
        return self.active_processes.copy()
    
    def stop_bot_process(self, session_id: str) -> bool:
        """
        Stop a specific bot process.
        
        Args:
            session_id: Session identifier for the process to stop
        
        Returns:
            bool: True if stopped successfully, False otherwise
        """
        try:
            if session_id in self.active_processes:
                process_info = self.active_processes[session_id]
                
                # Remove from registry
                self.registry.remove(session_id)
                
                # Clean up tracking
                del self.active_processes[session_id]
                
                logger.info(f"Bot process {session_id} stopped successfully")
                return True
            else:
                logger.warning(f"No active process found for session {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error stopping bot process {session_id}: {e}")
            return False
    
    def get_process_status(self, session_id: str) -> Optional[dict]:
        """
        Get status information for a specific process.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Optional[dict]: Process status information or None if not found
        """
        process_info = self.active_processes.get(session_id)
        if process_info:
            return {
                "session_id": session_id,
                "agent_name": process_info["agent_name"],
                "started_at": process_info["started_at"],
                "is_active": process_info["thread"].is_alive(),
                "call_id": process_info["context"]["call_id"]
            }
        return None