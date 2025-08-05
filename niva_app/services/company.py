"""
Module: custard_app.services.company

This module contains the company service functions. These functions are used to create and manage companies and their agents.

Functions:
    - create_company: Create a company with the provided details.
"""
import traceback
import threading
from typing import Optional, Tuple
from jsonschema import validate, ValidationError
import logging

from django.utils import timezone
from django.db.models import QuerySet
from django.core.management import call_command

from custard_app.models.users import User

from custard_app.models import Company, Agent

logger = logging.getLogger(__name__)

class CompanyService:
    def __init__(self):
        pass

    def create_company(
        self,
        name: str,
        address: str = "",
        time_zone: str = "Asia/Kolkata",
        phone_number: str = None,
    ) -> Company:
        """
        Create a new company with the provided details.
        """
        company = Company(
            name=name,
            address=address,
            time_zone=time_zone,
            phone_number=phone_number,
        )
        company.save()
        return company
    
    def get_company_by_name(self, company_name: str) -> Optional[dict]:
        """
        Retrieve a company's details by its name. If multiple companies exist, returns the first one.
        """
        try:
            company = Company.objects.filter(name=company_name).first()
            if not company:
                return None
            return {
                "id": company.id,
                "name": company.name,
                "address": company.address,
                "time_zone": str(company.time_zone),
                "phone_number": company.phone_number.phone_number if company.phone_number else None,
                "inbound_agent_id": company.inbound_agent.id if company.inbound_agent else None,
                "outbound_agent_id": company.outbound_agent.id if company.outbound_agent else None,
            }
        except Exception as e:
            logger.error(f"Error fetching company by name: {str(e)}")
            return None
    
    def get_company_by_id(self, company_id: int) -> Optional[Company]:
        """
        Retrieve a company by its ID.
        """
        try:
            return Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return None

    def create_agent(
        self,
        name: str,
        company: Company,
        prompt: str = "Hello, how can I help you?",
        is_inbound: bool = False,
        is_active: bool = True,
        language: str = "en",
    ) -> Agent:
        """
        Create an agent associated with a company and update company references.
        """
        agent = Agent.objects.create(
            name=name,
            company=company,
            prompt=prompt,
            is_inbound=is_inbound,
            is_active=is_active,
            language=language,
        )
        
        # Update company's agent references
        if is_inbound:
            company.inbound_agent = agent
        else:
            company.outbound_agent = agent
        company.save()
        
        return agent

    def get_agent_by_company(self, company: Company) -> Optional[Agent]:
        """
        Retrieve an agent by its associated company.
        """
        try:
            return Agent.objects.filter(company=company).first()
        except Agent.DoesNotExist:
            return None

    def get_agents_by_company(self, company: Company) -> QuerySet[Agent]:
        """
        Retrieve all agents by their associated company.
        """
        return Agent.objects.filter(company=company)

    def get_agent_by_company_id(self, company_id: int) -> Optional[Agent]:
        """
        Retrieve an agent by its associated company ID.
        """
        try:
            return Agent.objects.filter(company__id=company_id).first()
        except Agent.DoesNotExist:
            return None

    def get_agent_by_company_name(self, company_name: str) -> Optional[Agent]:
        """
        Retrieve an agent by its associated company name.
        """
        try:
            return Agent.objects.filter(company__name=company_name).first()
        except Agent.DoesNotExist:
            return None

    def get_agent_by_id(self, agent_id: int) -> Optional[Agent]:
        """
        Retrieve an agent by its ID.
        """
        try:
            return Agent.objects.get(id=agent_id)
        except Agent.DoesNotExist:
            return None

    def update_company_agent_references(self, company: Company, agent: Agent, is_active: bool):
        """
        Update company's agent references based on agent status.
        """
        if not is_active:
            # Remove agent from company references when deactivated
            if company.inbound_agent == agent:
                company.inbound_agent = None
            if company.outbound_agent == agent:
                company.outbound_agent = None
        else:
            # Set agent back to company references when activated
            if agent.is_inbound:
                company.inbound_agent = agent
            else:
                company.outbound_agent = agent
        company.save()

    def get_company_agent_info(self, company: Company) -> dict:
        """
        Get company agent information including which agents are set as inbound/outbound.
        """
        return {
            "inbound_agent": {
                "id": company.inbound_agent.id,
                "name": company.inbound_agent.name,
                "is_active": company.inbound_agent.is_active,
            } if company.inbound_agent else None,
            "outbound_agent": {
                "id": company.outbound_agent.id,
                "name": company.outbound_agent.name,
                "is_active": company.outbound_agent.is_active,
            } if company.outbound_agent else None,
        }

    #TODO: To be done in future
    # def update_twilio_phone_number(self, location_id, twilio_phone_number):
    #     """
    #     Update Twilio number for the location

    #     Args:
    #         location_id (int): Location ID
    #         twilio_phone_number (str): Twilio phone number

    #     Returns:
    #         Location: Updated location object
    #     """
    #     location = Location.objects.get(id=location_id)
    #     location.twilio_phone_number = twilio_phone_number
    #     location.save()
    #     return location
    
    def update_flow_content(self, location, flow_content, previous_version, integration_type):
        """
        Implement logic to update the pipecat flow file (changes to be reflected in db with version number)
        """
        pass

    def validate_flow_content(self, flow_content, service_type):
        """
        Implement logic to validate pipecat flow file
        """
        pass