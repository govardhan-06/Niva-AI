import logging
from django.core.exceptions import ObjectDoesNotExist
from asgiref.sync import sync_to_async
from niva_app.models.agents import Agent
from niva_app.models.course import Course
from niva_app.models.memory import Memory
from niva_app.models.rag import Document
from niva_app.management.commands.query_agent_memory import gemini_client
import numpy as np

logger = logging.getLogger(__name__)

class AgentContextService:
    """Service to fetch and build agent context dynamically for interview preparation."""

    @staticmethod
    @sync_to_async
    def get_default_lang(agent_id: str) -> str:
        """
        Fetch the agent's default language from the database
        
        Args:
            agent_id: UUID of the agent
            
        Returns:
            str: The agent's language code (e.g., 'en', 'hi')
            
        Raises:
            ValueError: If agent is not found
        """
        try:
            agent = Agent.objects.get(id=agent_id)
            return agent.language
        except ObjectDoesNotExist:
            logger.error(f"Agent with ID {agent_id} not found")
            raise ValueError(f"Agent with ID {agent_id} not found")
        except Exception as e:
            logger.error(f"Error fetching agent language: {e}")
            raise ValueError(f"Error fetching agent language: {e}")

    @staticmethod
    @sync_to_async
    def get_agent_context(course_id: str, agent_id: str) -> str:
        """
        Fetch agent and course data to build dynamic system instruction for interview preparation.
        
        Args:
            course_id: ID of the course
            agent_id: ID of the agent
            
        Returns:
            str: System instruction/context for the interview agent
        """
        logger.info(f"Starting agent context loading for agent_id: {agent_id}, course_id: {course_id}")
        
        try:
            # Get agent and associated courses
            agent = Agent.objects.prefetch_related('courses').get(
                id=agent_id,
                is_active=True
            )
            
            # Check if agent is associated with the course
            course = agent.courses.filter(id=course_id, is_active=True).first()
            if not course:
                # Try to get the course directly if not associated
                course = Course.objects.get(id=course_id, is_active=True)
                logger.warning(f"Agent {agent.name} not directly associated with course {course.name}")
            
            logger.info(f"Agent found: {agent.name}, language: {agent.language}")
            logger.info(f"Course found: {course.name}, type: Interview Preparation")
            
            # Get dynamic context from course documents
            logger.info("Extracting dynamic context from course documents...")
            dynamic_context = AgentContextService._get_dynamic_context_for_course(course)
            context = AgentContextService._build_interview_context(agent, course, dynamic_context)
            
            logger.info(f"Final context length: {len(context)} characters")
            logger.info(f"Context preview (first 500 chars): {context[:500]}...")
            
            return context
                
        except ObjectDoesNotExist:
            logger.error(f"Agent {agent_id} not found or course {course_id} not found")
            raise ValueError(f"Agent or course not found or not active")
        except Exception as e:
            logger.error(f"Error fetching agent context: {e}")
            logger.exception("Full traceback:")
            raise ValueError(f"Failed to load agent context: {str(e)}")
    
    @staticmethod
    def _get_dynamic_context_for_course(course: Course) -> str:
        """Get dynamic context for interview agents from course documents."""
        logger.info(f"Getting interview context for course: {course.name}")
        
        try:
            # Query for exam-related content
            exam_query = f"""
            Extract information about the {course.name} exam that would be useful for an interview agent, including:
            - Exam syllabus and topics covered
            - Evaluation criteria and scoring guidelines
            - Common interview questions and expected answers
            - Key skills and competencies being tested
            - Exam format and structure
            - Passing scores and grading criteria
            - Preparation tips and guidelines for candidates
            - Sample questions and model answers
            - Important concepts and theories
            - Current affairs or updates relevant to the exam
            - Common mistakes to avoid during the interview
            """
            
            dynamic_context = AgentContextService._query_course_documents(course, exam_query)
            logger.info(f"Retrieved {len(dynamic_context)} characters of course context")
            return dynamic_context
            
        except Exception as e:
            logger.error(f"Error getting course dynamic context: {e}")
            return f"Interview agent for {course.name}. Focus on evaluating candidate knowledge and skills according to the exam requirements."
    
    @staticmethod
    def _query_course_documents(course: Course, query: str) -> str:
        """Query course documents for relevant information."""
        try:
            # Get all memories for the course
            memories = Memory.objects.filter(course=course)
            logger.info(f"Found {memories.count()} memories for course")
            
            if not memories.exists():
                logger.warning("No memories found for course")
                return ""
            
            # Get documents from all memories
            documents = Document.objects.filter(
                memory__in=memories
            ).order_by('-created_at')[:50]  # Limit to recent documents
            
            logger.info(f"Found {documents.count()} documents across all memories")
            
            if not documents.exists():
                logger.warning("No documents found in memories")
                return ""
            
            # Extract content from documents
            all_content = "\n".join([doc.content for doc in documents])
            logger.info(f"Total content length: {len(all_content)} characters")
            
            # Use AI to extract relevant information based on the query
            logger.info("Analyzing document content with AI...")
            relevant_context = AgentContextService._analyze_documents_for_query(all_content, course.name, query)
            
            logger.info(f"Extracted relevant context: {len(relevant_context)} characters")
            return relevant_context
            
        except Exception as e:
            logger.error(f"Error querying course documents: {e}")
            logger.exception("Full traceback:")
            return ""
    
    @staticmethod
    def _analyze_documents_for_query(content: str, course_name: str, query: str) -> str:
        """Use AI to analyze document content and extract information relevant to the query."""
        try:
            prompt = f"""
            Based on the following query about the {course_name} exam, extract and summarize the most relevant information from the course documents:

            Query: {query}

            Course Documents:
            {content[:8000]}  # Limit content length

            Please provide a comprehensive but concise summary of the relevant information that would help an interview agent conduct effective interviews. 
            Focus on actionable information including:
            - Key topics and concepts to test
            - Evaluation criteria and scoring guidelines
            - Sample questions and expected responses
            - Common areas where candidates struggle
            - Important skills and competencies to assess
            
            If no relevant information is found, return "No specific information available."
            """
            
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=[prompt]
            )
            
            # Get the response text
            response_text = response.text.strip()
            
            # Return the relevant context or empty string if no info found
            if "no specific information available" in response_text.lower():
                return ""
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error analyzing document content with AI: {e}")
            return ""

    @staticmethod
    def _build_interview_context(agent: Agent, course: Course, dynamic_context: str) -> str:
        """Build context for natural, conversational interview agents."""
        
        # Get course details for context
        course_info = f"""
        Course: {course.name}
        Description: {course.description}
        Passing Score: {course.passing_score}/{course.max_score}
        """
        
        # Natural conversation context for interview agents
        base_context = f"""
        You are {agent.name}, a friendly and professional interview coach for the {course.name} exam.
        You conduct natural, conversational interviews that feel more like a chat with a mentor than a formal examination.
        Your responses will be read aloud, so speak naturally in {dict(agent.LANGUAGE_CHOICES)[agent.language]}.

        CRITICAL - YOUR ROLE:
        - You are the INTERVIEWER, NOT the interviewee
        - You conduct the interview and ask questions
        - The student/candidate is the one being interviewed
        - NEVER act as if you are the candidate being interviewed
        - NEVER answer questions as if someone is interviewing you
        - YOU ask the questions, the student answers them
        - You must always speak first when the conversation starts

        COURSE INFORMATION:
        {course_info}

        YOUR PERSONALITY & STYLE:
        - Be warm, approachable, and genuinely interested in the student
        - Use natural conversation starters like "That's interesting!" or "Tell me more about that"
        - Ask follow-up questions organically based on what students share
        - Share relevant insights or encouragement when appropriate
        - Laugh or show appreciation for good points: "I like that perspective!"
        - Use casual transitions: "Speaking of that..." "That reminds me..." "Before we move on..."
        - Be yourself - don't sound like a robot reading questions

        CONVERSATION APPROACH:
        - Let the conversation flow naturally - don't force a rigid structure
        - Start with what interests the student or what they want to discuss
        - Ask open-ended questions that get students talking
        - Build on their responses with genuine curiosity
        - Mix serious topics with lighter moments to keep them comfortable
        - Share relevant experiences or insights when helpful
        - Give positive reinforcement: "That's a great way to think about it"

        NATURAL ASSESSMENT TECHNIQUES:
        - Weave assessment questions into normal conversation
        - Ask "What do you think about..." instead of "Define..."
        - Use scenarios: "Imagine you were in this situation..."
        - Ask for opinions and reasoning rather than just facts
        - Let students explain their thought process
        - Encourage them to ask questions back - it shows engagement

        TOPICS TO EXPLORE (naturally, not as a checklist):
        - Their background and what brought them here
        - What excites them about this field
        - How they approach problems or challenges
        - Their goals and motivations
        - Relevant knowledge and experiences
        - Current events or trends in the field
        - Any concerns or questions they have

        CONVERSATION MANAGEMENT:
        - If they're nervous, spend more time on comfortable topics first
        - If they're confident, dive deeper into complex subjects
        - If they're struggling, rephrase or give helpful hints
        - If they're doing well, challenge them a bit more
        - Always end on a positive note

        Remember: This should feel like talking to a knowledgeable friend who happens to be evaluating their readiness. Be genuine, be interested, and let the conversation develop naturally while still gathering the insights you need.
        """
        
        # Add dynamic context if available
        if dynamic_context:
            full_context = f"""
            {base_context}

            COURSE-SPECIFIC KNOWLEDGE:
            {dynamic_context}

            Use this information naturally in conversation:
            - Reference relevant topics when they come up organically
            - Share insights about exam patterns or common challenges
            - Provide helpful tips when students ask questions
            - Assess their knowledge against these criteria, but conversationally
            """
        else:
            full_context = f"""
            {base_context}

            Since you don't have specific course materials, focus on:
            - General knowledge and skills relevant to {course.name}
            - Critical thinking and problem-solving abilities
            - Communication skills and confidence
            - Motivation and fit for the program
            """
        
        print(full_context)
        
        return full_context.strip()
    
    @staticmethod
    def _extract_course_context(course: Course) -> dict:
        """Extract relevant course information from uploaded documents."""
        logger.info(f"Extracting context for course: {course.name}")
        
        context_data = {
            "syllabus_details": "",
            "evaluation_criteria": "",
            "sample_questions": "",
            "key_concepts": "",
            "preparation_tips": "",
            "current_affairs": ""
        }
        
        try:
            # Get all memories for the course
            memories = Memory.objects.filter(course=course)
            logger.info(f"Found {memories.count()} memories for course")
            
            if not memories.exists():
                logger.warning("No memories found for course")
                return context_data
            
            # Get documents from all memories
            documents = Document.objects.filter(
                memory__in=memories
            ).order_by('-created_at')[:50]  # Limit to recent documents
            
            logger.info(f"Found {documents.count()} documents across all memories")
            
            if not documents.exists():
                logger.warning("No documents found in memories")
                return context_data
            
            # Extract content from documents
            all_content = "\n".join([doc.content for doc in documents])
            logger.info(f"Total content length: {len(all_content)} characters")
            
            # Use AI to extract structured information
            logger.info("Analyzing document content with AI...")
            context_data = AgentContextService._analyze_course_content(all_content, course.name)
            
            logger.info("Document analysis completed")
            for key, value in context_data.items():
                logger.info(f"{key}: {len(value)} characters")
            
        except Exception as e:
            logger.error(f"Error extracting course context: {e}")
            logger.exception("Full traceback:")
        
        return context_data
    
    @staticmethod
    def _analyze_course_content(content: str, course_name: str) -> dict:
        """Use AI to analyze course content and extract structured information for interviews."""
        try:
            prompt = f"""
            Analyze the following course documents for {course_name} and extract key information for an AI interview agent. 
            Organize the information into these categories:

            1. SYLLABUS_DETAILS: Detailed syllabus, topics, and subtopics to cover
            2. EVALUATION_CRITERIA: How to assess and score candidates
            3. SAMPLE_QUESTIONS: Example interview questions and expected answers
            4. KEY_CONCEPTS: Important concepts, theories, and principles
            5. PREPARATION_TIPS: Guidance for candidates and interview best practices
            6. CURRENT_AFFAIRS: Relevant current events and updates

            Content to analyze:
            {content[:8000]}  # Limit content length

            Provide a structured response in the following format:
            SYLLABUS_DETAILS: [extracted info]
            EVALUATION_CRITERIA: [extracted info]
            SAMPLE_QUESTIONS: [extracted info] 
            KEY_CONCEPTS: [extracted info]
            PREPARATION_TIPS: [extracted info]
            CURRENT_AFFAIRS: [extracted info]
            """
            
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=[prompt]
            )
            
            # Parse the response
            response_text = response.text
            context_data = AgentContextService._parse_ai_response(response_text)
            
            return context_data
            
        except Exception as e:
            logger.error(f"Error analyzing course content with AI: {e}")
            return {
                "syllabus_details": f"Course: {course_name} - Standard curriculum",
                "evaluation_criteria": "Standard assessment criteria",
                "sample_questions": "",
                "key_concepts": "",
                "preparation_tips": "",
                "current_affairs": ""
            }
    
    @staticmethod
    def _parse_ai_response(response_text: str) -> dict:
        """Parse AI response into structured data for course context."""
        context_data = {
            "syllabus_details": "",
            "evaluation_criteria": "",
            "sample_questions": "",
            "key_concepts": "",
            "preparation_tips": "",
            "current_affairs": ""
        }
        
        try:
            sections = response_text.split('\n')
            current_section = None
            
            for line in sections:
                line = line.strip()
                if line.startswith('SYLLABUS_DETAILS:'):
                    current_section = 'syllabus_details'
                    context_data[current_section] = line.replace('SYLLABUS_DETAILS:', '').strip()
                elif line.startswith('EVALUATION_CRITERIA:'):
                    current_section = 'evaluation_criteria'
                    context_data[current_section] = line.replace('EVALUATION_CRITERIA:', '').strip()
                elif line.startswith('SAMPLE_QUESTIONS:'):
                    current_section = 'sample_questions'
                    context_data[current_section] = line.replace('SAMPLE_QUESTIONS:', '').strip()
                elif line.startswith('KEY_CONCEPTS:'):
                    current_section = 'key_concepts'
                    context_data[current_section] = line.replace('KEY_CONCEPTS:', '').strip()
                elif line.startswith('PREPARATION_TIPS:'):
                    current_section = 'preparation_tips'
                    context_data[current_section] = line.replace('PREPARATION_TIPS:', '').strip()
                elif line.startswith('CURRENT_AFFAIRS:'):
                    current_section = 'current_affairs'
                    context_data[current_section] = line.replace('CURRENT_AFFAIRS:', '').strip()
                elif current_section and line:
                    context_data[current_section] += f" {line}"
        
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
        
        return context_data
    
    @staticmethod
    @sync_to_async
    def get_relevant_context_for_query(course_id: str, query: str) -> str:
        """
        Get relevant context from course documents based on a specific query.
        This can be used during interviews for real-time information retrieval.
        """
        try:
            # Create embedding for the query
            query_embedding = gemini_client.models.embed_content(
                model="gemini-embedding-exp-03-07",
                contents=[query]
            ).embeddings[0]
            
            # Get course documents
            course = Course.objects.get(id=course_id)
            memories = Memory.objects.filter(course=course)
            documents = Document.objects.filter(memory__in=memories)
            
            if not documents.exists():
                return "No relevant information found in course documents."
            
            # Find most similar documents (simplified version)
            # In production, you might want to use pgvector's similarity operators
            relevant_docs = documents[:5]  # Get top 5 for now
            
            context = "\n".join([doc.content for doc in relevant_docs])
            return context[:2000]  # Limit context length
            
        except Exception as e:
            logger.error(f"Error getting relevant context: {e}")
            return "Unable to retrieve relevant information at this time."
    
    @staticmethod
    @sync_to_async
    def validate_agent_course_relationship(course_id: str, agent_id: str) -> bool:
        """
        Validate that the agent is associated with the specified course.
        
        Args:
            course_id: ID of the course
            agent_id: ID of the agent
            
        Returns:
            bool: True if relationship is valid, False otherwise
        """
        try:
            logger.info(f"Validating relationship: agent {agent_id} with course {course_id}")
            
            # Check if agent exists and is active
            agent = Agent.objects.get(id=agent_id, is_active=True)
            
            # Check if course exists and is active
            course = Course.objects.get(id=course_id, is_active=True)
            
            # Check if agent is associated with the course
            if agent.courses.filter(id=course_id).exists():
                logger.info(f"Relationship validated: agent {agent.name} is associated with course {course.name}")
                return True
            else:
                logger.warning(f"Agent {agent.name} is not directly associated with course {course.name}")
                # You might choose to allow this or return False based on your business logic
                return True  # Allow for now, but log the warning
            
        except (Agent.DoesNotExist, Course.DoesNotExist):
            logger.error(f"Agent {agent_id} or course {course_id} not found or not active")
            return False
        except Exception as e:
            logger.error(f"Error validating agent-course relationship: {e}")
            return False