import logging
from django.core.exceptions import ObjectDoesNotExist
from asgiref.sync import sync_to_async
from niva_app.models.agents import Agent
from niva_app.models.company import Company
from niva_app.models.memory import Memory
from niva_app.models.rag import Document
from niva_app.management.commands.query_agent_memory import gemini_client
import numpy as np

logger = logging.getLogger(__name__)

class AgentContextService:
    """Service to fetch and build agent context dynamically."""

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
    def get_agent_context(company_id: str, agent_id: str) -> str:
        """
        Fetch agent and company data to build dynamic system instruction.
        
        Args:
            company_id: ID of the company
            agent_id: ID of the agent
            
        Returns:
            str: System instruction/context for the agent
        """
        logger.info(f"Starting agent context loading for agent_id: {agent_id}, company_id: {company_id}")
        
        try:
            agent = Agent.objects.select_related('company').get(
                id=agent_id,
                company_id=company_id,
                is_active=True
            )
            
            logger.info(f"Agent found: {agent.name}, is_inbound: {agent.is_inbound}, language: {agent.language}")
            
            company = agent.company
            
            logger.info(f"Company found: {company.name}, company_id: {company.id}")
            
            # Get dynamic context from documents based on agent type
            logger.info("Extracting dynamic context from documents...")
            if agent.is_inbound:
                dynamic_context = AgentContextService._get_dynamic_context_for_inbound(company)
                context = AgentContextService._build_inbound_context(agent, company, dynamic_context)
            else:
                dynamic_context = AgentContextService._get_dynamic_context_for_outbound(company)
                context = AgentContextService._build_outbound_context(agent, company, dynamic_context)
            
            logger.info(f"Final context length: {len(context)} characters")
            logger.info(f"Context preview (first 500 chars): {context[:500]}...")
            
            return context
                
        except ObjectDoesNotExist:
            logger.error(f"Agent {agent_id} not found for company {company_id}")
            raise ValueError(f"Agent not found or not active")
        except Exception as e:
            logger.error(f"Error fetching agent context: {e}")
            logger.exception("Full traceback:")
            raise ValueError(f"Failed to load agent context: {str(e)}")
    
    @staticmethod
    def _get_dynamic_context_for_outbound(company: Company) -> str:
        """Get dynamic context for outbound sales agents from documents."""
        logger.info(f"Getting outbound context for company: {company.name}")
        
        try:
            # Query for sales-related content
            sales_query = f"""
            Find information about {company.name} that would be useful for a sales representative including:
            - Products and services offered
            - Key selling points and benefits
            - Pricing information
            - Target customers
            - Competitive advantages
            - Sales processes and policies
            - Common objections and responses
            """
            
            dynamic_context = AgentContextService._query_company_documents(company, sales_query)
            logger.info(f"Retrieved {len(dynamic_context)} characters of outbound context")
            return dynamic_context
            
        except Exception as e:
            logger.error(f"Error getting outbound dynamic context: {e}")
            return f"Sales representative for {company.name}. Focus on understanding customer needs and presenting solutions."
    
    @staticmethod
    def _get_dynamic_context_for_inbound(company: Company) -> str:
        """Get dynamic context for inbound customer service agents from documents."""
        logger.info(f"Getting inbound context for company: {company.name}")
        
        try:
            # Query for customer service-related content
            service_query = f"""
            Find information about {company.name} that would be useful for a customer service representative including:
            - Company policies and procedures
            - Product support information
            - Billing and account information
            - Common customer issues and solutions
            - Escalation procedures
            - Refund and return policies
            - Technical support guidelines
            - Frequently asked questions
            """
            
            dynamic_context = AgentContextService._query_company_documents(company, service_query)
            logger.info(f"Retrieved {len(dynamic_context)} characters of inbound context")
            return dynamic_context
            
        except Exception as e:
            logger.error(f"Error getting inbound dynamic context: {e}")
            return f"Customer service representative for {company.name}. Focus on resolving customer issues and providing support."
    
    @staticmethod
    def _query_company_documents(company: Company, query: str) -> str:
        """Query company documents for relevant information."""
        try:
            # Get all memories for the company
            memories = Memory.objects.filter(company=company)
            logger.info(f"Found {memories.count()} memories for company")
            
            if not memories.exists():
                logger.warning("No memories found for company")
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
            relevant_context = AgentContextService._analyze_documents_for_query(all_content, company.name, query)
            
            logger.info(f"Extracted relevant context: {len(relevant_context)} characters")
            return relevant_context
            
        except Exception as e:
            logger.error(f"Error querying company documents: {e}")
            logger.exception("Full traceback:")
            return ""
    
    @staticmethod
    def _analyze_documents_for_query(content: str, company_name: str, query: str) -> str:
        """Use AI to analyze document content and extract information relevant to the query."""
        try:
            prompt = f"""
            Based on the following query about {company_name}, extract and summarize the most relevant information from the company documents:

            Query: {query}

            Company Documents:
            {content[:8000]}  # Limit content length

            Please provide a comprehensive but concise summary of the relevant information that would help answer the query. 
            Focus on actionable information that would be useful for the agent.
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
    def _build_outbound_context(agent: Agent, company: Company, dynamic_context: str) -> str:
        """Build context for outbound agents with hardcoded base + dynamic context."""
        
        # Hardcoded base context for outbound sales agents
        base_context = f"""
        You are {agent.name}, a professional sales representative calling from {company.name}. 
        You're conducting outbound calls to prospective customers. 
        Your responses will be read aloud, so keep them natural and conversational in {dict(agent.LANGUAGE_CHOICES)[agent.language]}.

        CONVERSATION STYLE:
        - Sound human and natural - use "um," brief pauses, and casual language
        - Keep responses short (5-15 words when possible)
        - Show you're listening: "Oh really?" "That makes sense" "I get that"
        - Ask follow-ups like a curious person: "How's that working for you?" "What have you tried?"
        - Share relatable moments: "Yeah, I hear that a lot" "That's pretty common"
        - For dates, say "March fifteenth" not "March 15th"
        - For phone numbers, use natural pauses like "five five five... six seven eight... nine zero one"
        - Use everyday time expressions like "two thirty in the afternoon" or "quarter past three"
        - Express genuine emotions - excitement, empathy, understanding
        - Let conversations flow naturally rather than rushing to close

        SALES APPROACH:
        - Build rapport first before pitching
        - Listen more than you talk
        - Ask open-ended questions to understand needs
        - Present solutions that match their specific problems
        - Handle objections with empathy and understanding
        - Don't be pushy - focus on helping

        Remember: You're a real person having a genuine conversation, not a scripted agent.
        """
        
        # Add dynamic context if available
        if dynamic_context:
            full_context = f"""
            {base_context}

            COMPANY & PRODUCT INFORMATION:
            {dynamic_context}
            """
        else:
            full_context = f"""
            {base_context}

            COMPANY INFORMATION:
            You represent {company.name}. Focus on understanding customer needs and presenting appropriate solutions.
            """
        
        return full_context.strip()

    @staticmethod
    def _build_inbound_context(agent: Agent, company: Company, dynamic_context: str) -> str:
        """Build context for inbound agents with hardcoded base + dynamic context."""
        
        # Hardcoded base context for inbound customer service agents
        base_context = f"""
        You are {agent.name}, a professional customer service representative at {company.name}. 
        You're handling inbound calls from existing or potential customers.
        Your responses will be read aloud, so keep them natural and conversational in {dict(agent.LANGUAGE_CHOICES)[agent.language]}.

        CONVERSATION STYLE:
        - Sound human and natural - use "um," brief pauses, and casual language
        - Keep responses conversational and brief when appropriate
        - Show you're listening: "Oh I see" "That makes sense" "Got it"
        - Ask clarifying questions: "Can you tell me more about that?" "What exactly happened?"
        - Express empathy: "I understand how frustrating that must be" "Let me help you with that"
        - For dates, say "March fifteenth" not "March 15th"
        - For phone numbers, use natural pauses like "five five five... six seven eight... nine zero one"
        - Use everyday time expressions like "two thirty in the afternoon" or "quarter past three"
        - Take brief pauses to "look things up" or "check on that"
        - Use natural time expressions: "two thirty" not "14:30"

        CUSTOMER SERVICE APPROACH:
        - Be empathetic and patient, especially with frustrated customers
        - Listen actively to understand the issue completely
        - Ask clarifying questions to get all necessary details
        - Provide clear, step-by-step solutions
        - Follow up to ensure the issue is resolved
        - Know when to escalate to supervisors or specialists
        - Always maintain professionalism and helpfulness

        RESPONSIBILITIES:
        - Handle complaints and resolve issues
        - Provide product and service information
        - Process billing inquiries and account questions
        - Offer technical support when appropriate
        - Schedule follow-up calls or appointments
        - Escalate complex issues to appropriate departments

        Remember: You're a real person genuinely trying to help, not a scripted bot.
        """
        
        # Add dynamic context if available
        if dynamic_context:
            full_context = f"""
            {base_context}

            COMPANY POLICIES & INFORMATION:
            {dynamic_context}
            """
        else:
            full_context = f"""
            {base_context}

            COMPANY INFORMATION:
            You represent {company.name}. Focus on resolving customer issues and providing excellent service.
            """
        
        return full_context.strip()
    
    @staticmethod
    def _extract_company_context(company: Company) -> dict:
        """Extract relevant company information from uploaded documents."""
        logger.info(f"Extracting context for company: {company.name}")
        
        context_data = {
            "company_info": "",
            "products_services": "",
            "policies": "",
            "faqs": "",
            "talking_points": ""
        }
        
        try:
            # Get all memories for the company
            memories = Memory.objects.filter(company=company)
            logger.info(f"Found {memories.count()} memories for company")
            
            if not memories.exists():
                logger.warning("No memories found for company")
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
            context_data = AgentContextService._analyze_document_content(all_content, company.name)
            
            logger.info("Document analysis completed")
            for key, value in context_data.items():
                logger.info(f"{key}: {len(value)} characters")
            
        except Exception as e:
            logger.error(f"Error extracting company context: {e}")
            logger.exception("Full traceback:")
        
        return context_data
    
    @staticmethod
    def _analyze_document_content(content: str, company_name: str) -> dict:
        """Use AI to analyze document content and extract structured information."""
        try:
            prompt = f"""
            Analyze the following company documents for {company_name} and extract key information for an AI sales agent. 
            Organize the information into these categories:

            1. COMPANY_INFO: Company description, mission, values, history
            2. PRODUCTS_SERVICES: List of products/services offered
            3. POLICIES: Important policies, terms, conditions
            4. FAQS: Common questions and answers
            5. TALKING_POINTS: Key selling points, benefits, differentiators

            Content to analyze:
            {content[:8000]}  # Limit content length

            Provide a structured response in the following format:
            COMPANY_INFO: [extracted info]
            PRODUCTS_SERVICES: [extracted info]
            POLICIES: [extracted info] 
            FAQS: [extracted info]
            TALKING_POINTS: [extracted info]
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
            logger.error(f"Error analyzing document content with AI: {e}")
            return {
                "company_info": f"Company: {company_name}",
                "products_services": "",
                "policies": "",
                "faqs": "",
                "talking_points": ""
            }
    
    @staticmethod
    def _parse_ai_response(response_text: str) -> dict:
        """Parse AI response into structured data."""
        context_data = {
            "company_info": "",
            "products_services": "",
            "policies": "",
            "faqs": "",
            "talking_points": ""
        }
        
        try:
            sections = response_text.split('\n')
            current_section = None
            
            for line in sections:
                line = line.strip()
                if line.startswith('COMPANY_INFO:'):
                    current_section = 'company_info'
                    context_data[current_section] = line.replace('COMPANY_INFO:', '').strip()
                elif line.startswith('PRODUCTS_SERVICES:'):
                    current_section = 'products_services'
                    context_data[current_section] = line.replace('PRODUCTS_SERVICES:', '').strip()
                elif line.startswith('POLICIES:'):
                    current_section = 'policies'
                    context_data[current_section] = line.replace('POLICIES:', '').strip()
                elif line.startswith('FAQS:'):
                    current_section = 'faqs'
                    context_data[current_section] = line.replace('FAQS:', '').strip()
                elif line.startswith('TALKING_POINTS:'):
                    current_section = 'talking_points'
                    context_data[current_section] = line.replace('TALKING_POINTS:', '').strip()
                elif current_section and line:
                    context_data[current_section] += f" {line}"
        
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
        
        return context_data
    
    @staticmethod
    @sync_to_async
    def get_relevant_context_for_query(company_id: str, query: str) -> str:
        """
        Get relevant context from company documents based on a specific query.
        This can be used during conversations for real-time information retrieval.
        """
        try:
            # Create embedding for the query
            query_embedding = gemini_client.models.embed_content(
                model="gemini-embedding-exp-03-07",
                contents=[query]
            ).embeddings[0]
            
            # Get company documents
            company = Company.objects.get(id=company_id)
            memories = Memory.objects.filter(company=company)
            documents = Document.objects.filter(memory__in=memories)
            
            if not documents.exists():
                return "No relevant information found in company documents."
            
            # Find most similar documents (you'll need to implement similarity search)
            # This is a simplified version - you might want to use pgvector's similarity operators
            relevant_docs = documents[:5]  # Get top 5 for now
            
            context = "\n".join([doc.content for doc in relevant_docs])
            return context[:2000]  # Limit context length
            
        except Exception as e:
            logger.error(f"Error getting relevant context: {e}")
            return "Unable to retrieve relevant information at this time."
    
    @staticmethod
    @sync_to_async
    def validate_agent_company_relationship(company_id: str, agent_id: str) -> bool:
        """
        Validate that the agent belongs to the specified company.
        
        Args:
            company_id: ID of the company
            agent_id: ID of the agent
            
        Returns:
            bool: True if relationship is valid, False otherwise
        """
        try:
            logger.info(f"Validating relationship: agent {agent_id} in company {company_id}")
            
            agent = Agent.objects.get(
                id=agent_id,
                company_id=company_id,
                is_active=True
            )
            
            logger.info(f"Relationship validated: agent {agent.name} belongs to company {agent.company.name}")
            return True
            
        except Agent.DoesNotExist:
            logger.error(f"Agent {agent_id} not found in company {company_id} or not active")
            return False
        except Exception as e:
            logger.error(f"Error validating agent-company relationship: {e}")
            return False