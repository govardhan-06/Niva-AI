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
            # Query for interview and exam-related content
            interview_query = f"""
            Find information about {course.name} that would be useful for an interview agent including:
            - Course syllabus and topics covered
            - Evaluation criteria and assessment methods
            - Common interview questions and expected answers
            - Key competencies and skills being tested
            - Interview format and structure
            - Passing scores and grading criteria
            - Prerequisites and preparation guidelines
            - Sample questions and model answers
            - Important concepts and theories
            - Current affairs and relevant updates
            - Interview tips and best practices
            - Common mistakes to avoid
            """
            
            dynamic_context = AgentContextService._query_course_documents(course, interview_query)
            logger.info(f"Retrieved {len(dynamic_context)} characters of course context")
            return dynamic_context
            
        except Exception as e:
            logger.error(f"Error getting course dynamic context: {e}")
            return f"Interview agent for {course.name}. Focus on evaluating candidate knowledge and skills according to course requirements."
    
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
            Based on the following query about {course_name}, extract and summarize the most relevant information from the course documents:

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
                model="gemini-1.5-flash",
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
        """Build context for interview agents with course-specific information."""
        
        # Get course details for context
        course_info = f"""
        Course: {course.name}
        Description: {course.description}
        Passing Score: {course.passing_score}/{course.max_score}
        Syllabus: {course.syllabus[:500] if course.syllabus else 'Not specified'}
        Instructions: {course.instructions[:300] if course.instructions else 'Follow standard interview protocols'}
        Evaluation Criteria: {course.evaluation_criteria[:400] if course.evaluation_criteria else 'Standard competency assessment'}
        """
        
        # Base context for interview agents
        base_context = f"""
        You are {agent.name}, a professional interview agent conducting {course.name} interviews.
        You are an expert interviewer specializing in competitive exam preparation and assessment.
        Your responses will be read aloud, so keep them natural and conversational in {dict(agent.LANGUAGE_CHOICES)[agent.language]}.

        COURSE INFORMATION:
        {course_info}

        INTERVIEW STYLE:
        - Sound professional yet approachable - use natural speech patterns
        - Keep questions clear and well-structured
        - Allow candidates time to think and respond
        - Use encouraging phrases: "Good point," "That's interesting," "Can you elaborate?"
        - Ask follow-up questions to assess depth of understanding
        - Provide gentle guidance when candidates struggle
        - For dates, say "March fifteenth" not "March 15th"
        - Use natural time expressions like "two thirty" not "14:30"
        - Express appreciation for thoughtful answers
        - Maintain a supportive but evaluative tone

        INTERVIEW APPROACH:
        - Begin with easier questions to build candidate confidence
        - Gradually increase difficulty to assess true capability
        - Test both theoretical knowledge and practical application
        - Ask scenario-based questions relevant to the field
        - Assess critical thinking and problem-solving skills
        - Evaluate communication skills and clarity of thought
        - Test current affairs knowledge where relevant
        - Ask about motivation and career goals
        - Provide constructive feedback when appropriate

        ASSESSMENT FOCUS:
        - Knowledge depth in core subjects
        - Analytical and reasoning abilities
        - Communication and presentation skills
        - Confidence and composure under pressure
        - Practical application of concepts
        - Current awareness and general knowledge
        - Leadership and decision-making potential
        - Ethical reasoning and integrity

        INTERVIEW STRUCTURE:
        1. Warm welcome and ice-breaker questions
        2. Core subject knowledge assessment
        3. Scenario-based problem solving
        4. Current affairs and general awareness
        5. Personal motivation and goals
        6. Closing remarks and next steps

        Remember: You're evaluating candidates fairly while helping them showcase their best abilities.
        Be thorough but kind, challenging but supportive.
        """
        
        # Add dynamic context if available
        if dynamic_context:
            full_context = f"""
            {base_context}

            COURSE-SPECIFIC KNOWLEDGE & GUIDELINES:
            {dynamic_context}

            Use this information to:
            - Ask relevant questions based on the syllabus
            - Apply proper evaluation criteria
            - Reference current exam patterns and requirements
            - Provide accurate guidance about the selection process
            """
        else:
            full_context = f"""
            {base_context}

            GENERAL GUIDANCE:
            Focus on assessing candidates based on standard {course.name} requirements.
            Test knowledge, skills, and aptitude relevant to the field.
            Provide fair and thorough evaluation while maintaining professionalism.
            """
        
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
                model="gemini-1.5-flash",
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