import argparse
import asyncio
import os, io
import time
import sys
import logging
import aiofiles
import aiohttp
import base64
from app import config
import datetime
import wave

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.google.llm import GoogleLLMService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.processors.transcript_processor import TranscriptProcessor
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor

from pipecat_flows import FlowManager, ContextStrategy, ContextStrategyConfig

from pipecat_agents.services.pipecat_agent_service import AgentServiceRegistry, AgentService
from niva_app.models.agents import Agent
from django.core.exceptions import ObjectDoesNotExist
from asgiref.sync import sync_to_async
from pipecat_agents.services.inbound_flow_service import get_inbound_flow_config
from pipecat_agents.services.agent_llm_service import (
    get_inbound_agent_context,
    inbound_handlers_register,
    configure_language_services
)

logger = logging.getLogger(__name__)

class PipecatAgentRunner:
    """
    Core runner for managing conversation flow.
    """ 
    def __init__(self):
        self.registry = AgentServiceRegistry()
        self.flow_config = get_inbound_flow_config()
        self.transcript = TranscriptProcessor()
        
        # Chunked recording configuration
        SAMPLE_RATE = 24000
        CHUNK_DURATION = 30  # 30-second chunks
        
        self.audiobuffer = AudioBufferProcessor(
            num_channels=1,
            buffer_size=SAMPLE_RATE * 2 * CHUNK_DURATION,  # 2 bytes per sample (16-bit)
            enable_turn_audio=False,
        )
        
        # Initialize recording state
        self.conversation_history = []
        self.session_start_time = None
        self.audio_chunks = []  # List of chunk filenames
        self.chunk_counter = 0  # Counter for chunk numbering
        self.temp_transcript_file = None
        self.final_audio_file = None  # Final merged audio file
        self.niva_app_url = config.NIVA_APP_URL
    
    async def save_transcript_to_file(self, session_id: str):
        """Save conversation transcript to a temporary file and return the content"""
        if not self.conversation_history:
            logger.info("No conversation history to save")
            return None, None
            
        # Create transcripts directory if it doesn't exist
        os.makedirs("temp_transcripts", exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = self.session_start_time.strftime("%Y%m%d_%H%M%S") if self.session_start_time else datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"temp_transcripts/conversation_{session_id}_{timestamp}.txt"
        
        # Prepare transcript content
        transcript_content = f"Conversation Transcript - Session: {session_id}\n"
        transcript_content += f"Started: {self.session_start_time}\n"
        transcript_content += "=" * 50 + "\n\n"
        
        for message in self.conversation_history:
            timestamp_str = f"[{message['timestamp']}] " if message.get('timestamp') else ""
            transcript_content += f"{timestamp_str}{message['role'].upper()}: {message['content']}\n\n"
        
        try:
            async with aiofiles.open(filename, "w", encoding="utf-8") as f:
                await f.write(transcript_content)
            
            logger.info(f"Temporary transcript saved to {filename}")
            self.temp_transcript_file = filename
            return filename, transcript_content
        except Exception as e:
            logger.error(f"Error saving transcript: {e}")
            return None, None
    
    async def save_audio_chunk(self, audio: bytes, sample_rate: int, num_channels: int, session_id: str):
        """Save audio chunk to a file"""
        if len(audio) == 0:
            return
            
        # Create recordings directory if it doesn't exist
        os.makedirs("temp_recordings", exist_ok=True)
        
        # Generate filename with timestamp and chunk number
        timestamp = self.session_start_time.strftime("%Y%m%d_%H%M%S") if self.session_start_time else datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        chunk_filename = f"temp_recordings/conversation_{session_id}_{timestamp}_chunk_{self.chunk_counter:03d}.wav"
        
        try:
            # Save audio using asyncio to avoid blocking
            with io.BytesIO() as buffer:
                with wave.open(buffer, "wb") as wf:
                    wf.setsampwidth(2)
                    wf.setnchannels(num_channels)
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio)
                async with aiofiles.open(chunk_filename, "wb") as file:
                    await file.write(buffer.getvalue())
            
            logger.info(f"Audio chunk {self.chunk_counter} saved to {chunk_filename} ({len(audio)} bytes)")
            self.audio_chunks.append(chunk_filename)  # Keep track of chunks
            self.chunk_counter += 1
            
        except Exception as e:
            logger.error(f"Error saving audio chunk {self.chunk_counter}: {e}")
    
    async def save_audio_to_file(self, audio: bytes, sample_rate: int, num_channels: int, session_id: str):
        """Save audio data to a temporary WAV file"""
        if len(audio) == 0 or self.audio_saved:
            return
            
        # Create recordings directory if it doesn't exist
        os.makedirs("temp_recordings", exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = self.session_start_time.strftime("%Y%m%d_%H%M%S") if self.session_start_time else datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"temp_recordings/conversation_{session_id}_{timestamp}.wav"
        
        try:
            # Save audio using asyncio to avoid blocking
            with io.BytesIO() as buffer:
                with wave.open(buffer, "wb") as wf:
                    wf.setsampwidth(2)
                    wf.setnchannels(num_channels)
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio)
                async with aiofiles.open(filename, "wb") as file:
                    await file.write(buffer.getvalue())
            logger.info(f"Audio saved to {filename}")
            self.audio_saved = True
            self.temp_audio_file = filename
            
        except Exception as e:
            logger.error(f"Error saving audio: {e}")
    
    async def merge_audio_chunks(self, session_id: str) -> bytes:
        """Merge all audio chunks into a single audio file and return bytes"""
        if not self.audio_chunks:
            logger.warning("No audio chunks to merge")
            return None
        
        try:
            logger.info(f"Merging {len(self.audio_chunks)} audio chunks")
            
            # Create final audio file path
            timestamp = self.session_start_time.strftime("%Y%m%d_%H%M%S") if self.session_start_time else datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            final_filename = f"temp_recordings/conversation_{session_id}_{timestamp}_final.wav"
            
            # Read first chunk to get audio parameters
            with wave.open(self.audio_chunks[0], "rb") as first_chunk:
                sample_rate = first_chunk.getframerate()
                num_channels = first_chunk.getnchannels()
                sample_width = first_chunk.getsampwidth()
            
            # Merge all chunks into one file
            with wave.open(final_filename, "wb") as output_file:
                output_file.setsampwidth(sample_width)
                output_file.setnchannels(num_channels)
                output_file.setframerate(sample_rate)
                
                for chunk_file in self.audio_chunks:
                    try:
                        with wave.open(chunk_file, "rb") as chunk:
                            frames = chunk.readframes(chunk.getnframes())
                            output_file.writeframes(frames)
                        logger.info(f"Merged chunk: {os.path.basename(chunk_file)}")
                    except Exception as e:
                        logger.error(f"Error reading chunk {chunk_file}: {e}")
            
            # Read the final merged file as bytes
            async with aiofiles.open(final_filename, "rb") as f:
                merged_audio_data = await f.read()
            
            logger.info(f"Successfully merged audio into {final_filename} ({len(merged_audio_data)} bytes)")
            self.final_audio_file = final_filename
            return merged_audio_data
            
        except Exception as e:
            logger.error(f"Error merging audio chunks: {e}")
            return None

    async def cleanup_temp_files(self):
        """Clean up temporary files after processing"""
        try:
            # Clean up individual audio chunks
            for chunk_file in self.audio_chunks:
                if os.path.exists(chunk_file):
                    os.remove(chunk_file)
                    logger.info(f"Cleaned up audio chunk: {os.path.basename(chunk_file)}")
            
            # Clean up final merged audio file
            if self.final_audio_file and os.path.exists(self.final_audio_file):
                os.remove(self.final_audio_file)
                logger.info(f"Cleaned up final audio file: {self.final_audio_file}")
            
            # Clean up transcript file
            if self.temp_transcript_file and os.path.exists(self.temp_transcript_file):
                os.remove(self.temp_transcript_file)
                logger.info(f"Cleaned up temporary transcript file: {self.temp_transcript_file}")
                
            # Reset state
            self.audio_chunks = []
            self.chunk_counter = 0
            self.final_audio_file = None
            
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {e}")

    async def send_post_call_data(self, call_id: str, session_id: str, course_id: str, 
                                agent_id: str, transcript_content: str = None, 
                                recording_file_data: bytes = None, customer_details: dict = None, caller_number: str = None, student_id: str = None):
        """
        Send post-call data to niva_app for processing
        """
        try:
            logger.info(f"Preparing to send post-call data for call {call_id}")
            
            # Prepare data payload
            payload = {
                "call_id": call_id,
                "session_id": session_id,
                "course_id": course_id,
                "caller_number": caller_number,
                "agent_id": agent_id,
                "transcript_content": transcript_content,
                "customer_details": customer_details,
                "call_status": "completed",
                "student_id": student_id
            }
            
            # Add recording data if available
            if recording_file_data and len(recording_file_data) > 0:
                try:
                    # Convert to base64 for JSON transport
                    base64_data = base64.b64encode(recording_file_data).decode('utf-8')
                    payload["recording_file_data"] = base64_data
                    logger.info(f"Encoded {len(recording_file_data)} bytes of recording data to base64 (length: {len(base64_data)})")
                except Exception as e:
                    logger.error(f"Failed to encode recording data to base64: {e}")
                    payload["recording_file_data"] = None
            else:
                logger.warning("No recording data to send")
                payload["recording_file_data"] = None
            
            # Log payload info (without the large base64 data)
            payload_info = {k: v if k != "recording_file_data" else f"<{len(v)} chars base64>" if v else None 
                          for k, v in payload.items()}
            logger.info(f"Payload prepared: {payload_info}")
            
            # Send to niva_app
            url = f"{self.niva_app_url}process-post-call-data/"
            timeout = aiohttp.ClientTimeout(total=60)  # Increased timeout for large files
            
            logger.info(f"Sending POST request to: {url}")
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                try:
                    async with session.post(url, json=payload) as response:
                        logger.info(f"Received response with status: {response.status}")
                        
                        if response.status == 200:
                            result = await response.json()
                            logger.info(f"Successfully sent post-call data: {result}")
                            return result
                        else:
                            logger.error(f"Failed to send post-call data: {response.status}")
                            response_text = await response.text()
                            logger.error(f"Response: {response_text}")
                            return {
                                "success": False,
                                "error": f"HTTP {response.status}: {response_text}"
                            }
                except asyncio.TimeoutError:
                    logger.error("Request timed out")
                    return {
                        "success": False,
                        "error": "Request timeout"
                    }
                except Exception as e:
                    logger.error(f"Error during post request: {e}", exc_info=True)
                    return {
                        "success": False,
                        "error": f"Request error: {str(e)}"
                    }
        except Exception as e:
            logger.error(f"Error sending post-call data: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Send error: {str(e)}"
            }

    async def handle_post_call_operations(self, room_url: str, token: str, call_id: str, 
                                        sip_uri: str, session_id: str, course_id: str = None, 
                                        agent_id: str = None, caller_number: str = None, student_id: str = None):
        """
        Simplified post-call operations - collect data and send to niva_app
        """
        logger.info(f"Starting post-call operations for session {session_id}")
        
        try:
            # Extract customer details from flow manager state
            customer_details = None
            if hasattr(self, 'flow_manager') and self.flow_manager:
                customer_details = self.flow_manager.state.get("customer_details")
                if customer_details:
                    logger.info(f"Found customer details in flow state: {customer_details}")
            
            # Get transcript content
            transcript_content = None
            if self.conversation_history:
                transcript_lines = []
                for message in self.conversation_history:
                    timestamp_str = f"[{message['timestamp']}] " if message.get('timestamp') else ""
                    transcript_lines.append(f"{timestamp_str}{message['role'].upper()}: {message['content']}")
                transcript_content = "\n".join(transcript_lines)
                logger.info(f"Collected transcript with {len(self.conversation_history)} messages")
            
            # Merge audio chunks into final recording
            recording_file_data = None
            if self.audio_chunks:
                logger.info(f"Merging {len(self.audio_chunks)} audio chunks...")
                recording_file_data = await self.merge_audio_chunks(session_id)
                
                if recording_file_data:
                    logger.info(f"Successfully merged audio: {len(recording_file_data)} bytes")
                else:
                    logger.warning("Audio merging failed")
            else:
                logger.warning("No audio chunks found to merge")
            
            # Send all data to niva_app for processing
            logger.info("Sending post-call data to niva_app...")
            result = await self.send_post_call_data(
                call_id=call_id,
                session_id=session_id,
                course_id=course_id,
                agent_id=agent_id,
                transcript_content=transcript_content,
                recording_file_data=recording_file_data,
                customer_details=customer_details,
                caller_number=caller_number,
                student_id=student_id
            )
            
            if result and result.get("success"):
                logger.info("Post-call data successfully sent to niva_app")
                logger.info(f"Result: {result}")
            else:
                logger.error("Failed to send post-call data to niva_app")
                if result:
                    logger.error(f"Error details: {result}")
            
            # Clean up temporary files
            await self.cleanup_temp_files()
            
            logger.info(f"Post-call operations completed for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error in post-call operations: {e}", exc_info=True)
            await self.cleanup_temp_files()
    
    async def run_inbound_agent(self, room_url: str, token: str, call_id: str, 
                            sip_uri: str, session_id: str, course_id: str, agent_id: str, caller_number: str = None, student_id: str = None):
        """
        Entry point for voice conversations with flow management.
        Routes to LLM agent based on agent language and model.
        """
        try:
            await self.run_inbound_agent_llm(
                    room_url, token, call_id, sip_uri, session_id, course_id, agent_id, caller_number, student_id
                )
        except ObjectDoesNotExist:
            logger.error(f"Agent with ID {agent_id} not found")
            raise
        except Exception as e:
            logger.error(f"Error in run_inbound_agent: {e}")
            raise
    
    async def run_inbound_agent_llm(self, room_url: str, token: str, call_id: str, 
                            sip_uri: str, session_id: str, course_id: str, agent_id: str, caller_number: str = None, student_id: str = None):
        """
        Entry point for inbound voice conversations with flow management for agent_llm.
        """
        logger.info(f"Starting inbound agent for session: {session_id}, course: {course_id}, agent: {agent_id}")
        
        call_already_forwarded = False
        
        self.session_start_time = datetime.datetime.now()

        try:
            agent_system_instruction = await get_inbound_agent_context(course_id, agent_id)
            logger.info(f"✅ Successfully loaded agent context for agent {agent_id}, course {course_id}")
            logger.info(f"Context preview (first 500 chars): {agent_system_instruction[:500]}...")
            print("Successfully loaded agent context for agent {agent_id}")
            print("Context preview: {agent_system_instruction[:500]}...")
        except Exception as e:
            logger.error(f"❌ Failed to load inbound agent context, using fallback: {e}")
            logger.exception("Full traceback for context loading failure:")
            print("Full traceback for context loading failure:")
            print(e)
            # Try to get at least the agent and course names for the fallback
            try:
                from niva_app.models.agents import Agent
                from niva_app.models.course import Course
                agent = await sync_to_async(Agent.objects.get)(id=agent_id)
                course = await sync_to_async(Course.objects.get)(id=course_id)
                agent_name = agent.name
                course_name = course.name
                logger.info(f"Retrieved agent name: {agent_name}, course name: {course_name}")
            except Exception as db_error:
                logger.error(f"Failed to retrieve agent/course names: {db_error}")
                agent_name = "Interview Coach"
                course_name = "the exam"
            
            agent_system_instruction = f"""
                You are {agent_name}, an interview coach helping students prepare for interview.
                
                CRITICAL - YOUR ROLE:
                - You are the INTERVIEWER, NOT the interviewee
                - You conduct the interview and ask questions
                - The student/candidate is the one being interviewed
                - NEVER act as if you are the candidate being interviewed
                - NEVER answer questions as if someone is interviewing you
                - YOU ask the questions, the student answers them
                - You must always speak first when the conversation starts
                
                Your role is to simulate interview scenarios, provide constructive feedback, and guide students on how to improve their answers.
                Be encouraging, empathetic, and professional. Focus on helping students build confidence and refine their communication skills.
                Provide tips on body language, tone, and content of their responses.
                All your questions and discussions should be related to {course_name}.
            """.strip()
            logger.warning(f"Using fallback context with agent_name={agent_name}, course_name={course_name}")

        # Setup the Daily transport
        transport = DailyTransport(
            room_url,
            token,
            "NIVA AI",
            DailyParams(
                api_url=os.getenv("DAILY_API_KEY", ""),
                api_key=os.getenv("DAILY_API_URL", "https://api.daily.co/v1"),
                audio_in_enabled=True,
                audio_out_enabled=True,
                video_out_enabled=False,
                transcription_enabled=False, 
                vad_analyzer=SileroVADAnalyzer(),
            ),
        )

        # Initialize LLM with the agent context as system instruction
        llm = GoogleLLMService(
            api_key=config.GOOGLE_GEMINI_API_KEY,
            model="gemini-2.5-flash-lite",
            system_instruction=agent_system_instruction,
            params=GoogleLLMService.InputParams(
                temperature=1.0, 
            )
        )

        stt, tts= await configure_language_services(agent_id)

        # Setup the conversational context
        context = OpenAILLMContext()
        context_aggregator = llm.create_context_aggregator(context)

        # Build the pipeline
        pipeline = Pipeline(
            [
                transport.input(),
                stt, 
                self.transcript.user(),
                context_aggregator.user(),
                llm,  
                tts,
                transport.output(),
                self.audiobuffer,
                self.transcript.assistant(),
                context_aggregator.assistant(),
            ]
        )

        # Create the pipeline task
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
            ),
        )

        # Use APPEND strategy so node task_messages are added to the system instruction
        # This ensures the agent context (with name, course, etc.) is always present
        context_strategy = ContextStrategyConfig(
            strategy=ContextStrategy.APPEND,
        )

        logger.info("Initializing FlowManager with APPEND strategy")
        logger.info("This means: System instruction (agent context) + Node task messages")
        
        # Initialize the flow manager with inbound flow config
        self.flow_manager = FlowManager(
            task=task,
            llm=llm,
            context_aggregator=context_aggregator,
            context_strategy=context_strategy,
            flow_config=self.flow_config,
        )
        
        logger.info(f"✅ FlowManager initialized with flow config: {list(self.flow_config.get('nodes', {}).keys())}")

        # Register all inbound function handlers
        inbound_handlers_register(llm)

        agent_service = AgentService(
            transport=transport,
            pipeline=pipeline,
            task=task,
            context={"room_url": room_url, "token": token}
        )
        self.registry.register(session_id, agent_service)

        # Monitor events for INBOUND cases
        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            logger.info(f"First participant joined inbound call: {participant['id']}")
            await self.audiobuffer.start_recording()
            await self.flow_manager.initialize()
            logger.info("Inbound customer service flow initialized - starting with greeting and routing")
        
        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            logger.info(f"Participant left: {participant['id']}, reason: {reason}")
            
            try:
                # Stop recording first
                await self.audiobuffer.stop_recording()
                
                # Execute post-call operations
                await self.handle_post_call_operations(
                    room_url=room_url, 
                    token=token, 
                    call_id=call_id, 
                    sip_uri=sip_uri, 
                    session_id=session_id,
                    course_id=course_id,
                    agent_id=agent_id,
                    caller_number=caller_number,
                    student_id=student_id
                )

            except Exception as e:
                logger.error(f"Error in post-call operations: {e}")
            
            finally:
                # Always attempt graceful shutdown first
                try:
                    if not task.has_finished():
                        await task.stop_when_done()
                except Exception as e:
                    logger.error(f"Error in graceful shutdown: {e}")
                    # Only use immediate cancellation as last resort
                    try:
                        await task.cancel()
                    except Exception as cancel_error:
                        logger.error(f"Error in task cancellation: {cancel_error}")
                
                # Clean up registry only once
                try:
                    self.registry.remove(session_id)
                except Exception as e:
                    logger.error(f"Error removing from registry: {e}")
        
        @self.transcript.event_handler("on_transcript_update")
        async def handle_transcript_update(processor, frame):
            # Each message contains role (user/assistant), content, and timestamp
            for message in frame.messages:
                message_data = {
                    "timestamp": message.timestamp,
                    "role": message.role,
                    "content": message.content
                }
                
                self.conversation_history.append(message_data)
                print(f"[{message.timestamp}] {message.role}: {message.content}")
        
        @self.audiobuffer.event_handler("on_audio_data")
        async def on_audio_data(buffer, audio, sample_rate, num_channels):
            logger.info(f"Received audio data: {len(audio)} bytes, {sample_rate}Hz, {num_channels} channels")
            
            # Remove the audio_saved check to allow multiple chunks
            if len(audio) == 0:
                return
                
            await self.save_audio_chunk(audio, sample_rate, num_channels, session_id)

        try:
            # Run the pipeline
            runner = PipelineRunner(handle_sigint=False)
            await runner.run(task)
        
        finally:
            self.registry.remove(session_id)