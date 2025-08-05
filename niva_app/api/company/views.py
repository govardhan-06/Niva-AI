import os
from django.core.validators import EmailValidator
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework import status
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_401_UNAUTHORIZED, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_204_NO_CONTENT
from typing import Optional
from rest_framework import serializers
from drf_yasg.utils import swagger_auto_schema
from datetime import datetime

from custard_app.api.common.views import BaseAPI
from custard_app.api.company.serializers import (
    CreateCompanyInputSerializer,
    DisableInputSerializer,
    UpdateCompanyInputSerializer,
    AddCompanyPhoneInputSerializer,
    UpdateCompanyPhoneInputSerializer
)
from custard_app.models.agents import Agent
from custard_app.services.company import CompanyService
from custard_app.models import Company
from custard_app.services.company_phone import CompanyPhoneService
from custard_app.models.phonenumber import PhoneNumber

class CreateCompany(BaseAPI):
    input_serializer_class = CreateCompanyInputSerializer

    def post(self, request, *args, **kwargs):
        """
        Create a new company.
        """
        data = self.validate_input_data()
        user = self.get_user()

        company_service = CompanyService()
        company: Company = company_service.create_company(
            name=data["name"],
            address=data["address"],
            time_zone=data["time_zone"],
        )

        # If the company is created successfully, we need to create default agents for the company
        if company:
            # Create default outbound agent
            outbound_agent = company_service.create_agent(
                name=f"{company.name} Outbound Agent",
                company=company,
                prompt="Hello, how can I help you?",
                is_inbound=False,
                is_active=True,
                language='en'
            )

            # Create default inbound agent
            inbound_agent = company_service.create_agent(
                name=f"{company.name} Inbound Agent",
                company=company,
                prompt="Hello, thank you for calling. How can I assist you?",
                is_inbound=True,
                is_active=True,
                language='en'
            )

            if outbound_agent and inbound_agent:
                response = {
                    "id": company.id,
                    "name": company.name,
                    "address": company.address,
                    "time_zone": company.time_zone.key,
                    "company_id": company.id,
                    "inbound_agent": {
                        "id": inbound_agent.id,
                        "name": inbound_agent.name,
                        "company_id": inbound_agent.company.id,
                        "prompt": inbound_agent.prompt,
                        "is_inbound": inbound_agent.is_inbound,
                        "is_active": inbound_agent.is_active,
                        "language": inbound_agent.language,
                        "created_at": inbound_agent.created_at,
                        "updated_at": inbound_agent.updated_at
                    },
                    "outbound_agent": {
                        "id": outbound_agent.id,
                        "name": outbound_agent.name,
                        "company_id": outbound_agent.company.id,
                        "prompt": outbound_agent.prompt,
                        "is_inbound": outbound_agent.is_inbound,
                        "is_active": outbound_agent.is_active,
                        "language": outbound_agent.language,
                        "created_at": outbound_agent.created_at,
                        "updated_at": outbound_agent.updated_at
                    },
                }

                return Response(response, status=HTTP_201_CREATED)
            else:
                return self.get_response_400("Agent creation failed")
        else:
            return self.get_response_400("Company creation failed")

class GetCompany(BaseAPI):
    """
    Get a company by ID.
    """

    def get(self, request, *args, **kwargs):
        """
        Get a company by ID.
        """
        company_id = self.kwargs.get("company_id")
        company_service = CompanyService()
        company: Optional[Company] = company_service.get_company_by_id(company_id)

        if company:
            # Fetch all agents and phone numbers for the company
            agents = company_service.get_agents_by_company(company)
            phones = CompanyPhoneService().get_phone_numbers_by_company(company_id)
            
            agents_data = [
                {
                    "id": str(agent.id),
                    "name": agent.name,
                    "company_id": agent.company.id,
                    "prompt": agent.prompt,
                    "is_inbound": agent.is_inbound,
                    "is_active": agent.is_active,
                    "language": agent.language,
                    "created_at": agent.created_at,
                    "updated_at": agent.updated_at,
                    "is_company_inbound_agent": company.inbound_agent == agent,
                    "is_company_outbound_agent": company.outbound_agent == agent,
                }
                for agent in agents
            ]

            # Get company agent info
            agent_info = company_service.get_company_agent_info(company)
            phone_data = [
                {
                    "id": str(phone.id),
                    "phone_number": str(phone.phone_number),
                    "sid": phone.sid,
                    "account_sid": phone.account_sid,
                    "voice_url": phone.voice_url,
                }
                for phone in phones
            ]

            response = {
                "id": str(company.id),
                "name": company.name,
                "address": company.address,
                "time_zone": company.time_zone.key,
                "company_id": company.id,
                "agents": agents_data,
                "phone_numbers": phone_data, 
            }

            if company.phone_number is not None:
                response["phone_number"] = company.phone_number.phone_number

            return Response(response, status=HTTP_200_OK)
        else:
            return self.get_response_400("Company not found")

class GetCompanyByName(BaseAPI):
    """
    Get a company by its name.
    """

    def get(self, request, *args, **kwargs):
        """
        Get a company by name.
        """
        company_name = request.query_params.get("name")
        if not company_name:
            return Response(
                {"error": "Company name is required as a query parameter."},
                status=HTTP_400_BAD_REQUEST,
            )

        company_service = CompanyService()
        company_details = company_service.get_company_by_name(company_name)

        if company_details:
            # Fetch all agents for the company
            company = Company.objects.get(id=company_details["id"])
            agents = company_service.get_agents_by_company(company)
            agents_data = []

            for agent in agents:
                agents_data.append({
                    "id": agent.id,
                    "name": agent.name,
                    "company_id": agent.company.id,
                    "prompt": agent.prompt,
                    "is_inbound": agent.is_inbound,
                    "is_active": agent.is_active,
                    "language": agent.language,
                    "created_at": agent.created_at,
                    "updated_at": agent.updated_at,
                    "is_company_inbound_agent": company.inbound_agent == agent,
                    "is_company_outbound_agent": company.outbound_agent == agent,
                })

            # Get company agent info
            agent_info = company_service.get_company_agent_info(company)

            phones = CompanyPhoneService().get_phone_numbers_by_company(company.id)
            
            phone_data = [
                {
                    "id": str(phone.id),
                    "phone_number": str(phone.phone_number),
                    "sid": phone.sid,
                    "account_sid": phone.account_sid,
                    "voice_url": phone.voice_url,
                }
                for phone in phones
            ]

            company_details.update({
                "phone_numbers": phone_data,
                "agents": agents_data,
                "company_agents": agent_info,
                })
            return Response(company_details, status=HTTP_200_OK)
        else:
            return Response({"error": "Company not found."}, status=HTTP_404_NOT_FOUND)

class UpdateCompany(BaseAPI):
    """
    Update basic company settings.
    """
    input_serializer_class = UpdateCompanyInputSerializer

    def validate_emails(self, emails):
        """
        Validate email list:
        - Maximum 3 emails
        - All emails must be unique
        - All emails must be valid
        """
        if not emails:
            return []

        if len(emails) > 3:
            raise ValidationError("Maximum 3 email addresses are allowed")

        # Remove duplicates while preserving order
        unique_emails = []
        seen = set()
        for email in emails:
            if email.lower() not in seen:
                seen.add(email.lower())
                unique_emails.append(email)

        # Validate email format
        email_validator = EmailValidator()
        for email in unique_emails:
            try:
                email_validator(email)
            except ValidationError:
                raise ValidationError(f"Invalid email format: {email}")

        return unique_emails

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()
        company_id = self.kwargs.get("company_id")
        user = self.get_user()

        # Check if user has access to this company
        if not user.has_company_access(company_id):
            return Response(
                {"detail": "You don't have access to this company"},
                status=HTTP_403_FORBIDDEN
            )

        company_service = CompanyService()
        company = company_service.get_company_by_id(company_id)

        if not company:
            return Response(
                {"detail": "Company not found"},
                status=HTTP_404_NOT_FOUND
            )
       
        try:
            company.name = data["name"]
            company.address = data["address"]
            company.time_zone = data["time_zone"]
            company.save()

            # Get all agents for the company
            agents = company_service.get_agents_by_company(company)
            agents_data = []

            for agent in agents:
                agents_data.append({
                    "id": agent.id,
                    "name": agent.name,
                    "company_id": agent.company.id,
                    "prompt": agent.prompt,
                    "is_inbound": agent.is_inbound,
                    "is_active": agent.is_active,
                    "language": agent.language,
                    "created_at": agent.created_at,
                    "updated_at": agent.updated_at,
                    "is_company_inbound_agent": company.inbound_agent == agent,
                    "is_company_outbound_agent": company.outbound_agent == agent,
                })

            # Get company agent info
            agent_info = company_service.get_company_agent_info(company)

            company_data = {
                "id": company.id,
                "name": company.name,
                "address": company.address,
                "time_zone": company.time_zone.key,
                "company_id": company.id,
                "agents": agents_data,
                "company_agents": agent_info,
            }

            self.set_response_message("Company settings updated successfully")
            return Response(company_data, status=HTTP_200_OK)

        except ValidationError as e:
            return self.get_response_400(str(e))

class AddCompanyPhone(BaseAPI):
    input_serializer_class = AddCompanyPhoneInputSerializer

    def post(self, request, *args, **kwargs):
        """
        Add a phone number to a company.
        """
        data = self.validate_input_data()
        company_id = self.kwargs.get("company_id")
        user = self.get_user()

        # Check if user has access to the company
        if not user.has_company_access(company_id):
            return Response(
                {"detail": "You don't have access to this company"},
                status=HTTP_400_BAD_REQUEST
            )

        phone_service = CompanyPhoneService()
        try:
            phone = phone_service.add_phone_number(
                company_id=company_id,
                phone_number=data["phone_number"],
                sid=data["sid"],
                account_sid=data["account_sid"],
                voice_url=data.get("voice_url"),
            )
            
            phone_data = {
                "id": str(phone.id),
                "phone_number": str(phone.phone_number),
                "sid": phone.sid,
                "account_sid": phone.account_sid,
                "voice_url": phone.voice_url,
            }
            return Response(phone_data, status=HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)

class UpdateCompanyPhone(BaseAPI):
    input_serializer_class = UpdateCompanyPhoneInputSerializer

    def post(self, request, *args, **kwargs):
        """
        Update a phone number for a company.
        """
        data = self.validate_input_data()
        company_id = self.kwargs.get("company_id")
        user = self.get_user()

        # Check if user has access to the company
        if not user.has_company_access(company_id):
            return Response(
                {"detail": "You don't have access to this company"},
                status=HTTP_400_BAD_REQUEST
            )

        phone_service = CompanyPhoneService()
        try:
            # Get the existing phone number for the company (assuming one-to-one relationship)
            existing_phone = PhoneNumber.objects.filter(company_id=company_id).first()
            if not existing_phone:
                return Response(
                    {"error": "No phone number found for this company."},
                    status=HTTP_404_NOT_FOUND
                )

            # Delete the existing phone number
            phone_service.delete_phone_number(existing_phone.id)

            # Add the new phone number
            new_phone = phone_service.add_phone_number(
                company_id=company_id,
                phone_number=data["phone_number"],
                sid=data.get("sid", existing_phone.sid),
                account_sid=data.get("account_sid", existing_phone.account_sid),
                voice_url=data.get("voice_url", existing_phone.voice_url),
            )
            
            phone_data = {
                "id": str(new_phone.id),
                "phone_number": str(new_phone.phone_number),
                "sid": new_phone.sid,
                "account_sid": new_phone.account_sid,
                "voice_url": new_phone.voice_url,
            }
            return Response(phone_data, status=HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)

class ListCompanyPhones(BaseAPI):
    """
    List all phone numbers for a company.
    """
    def get(self, request, *args, **kwargs):
        company_id = self.kwargs.get("company_id")
        user = self.get_user()

        if not user.has_company_access(company_id):
            return Response(
                {"detail": "You don't have access to this company"},
                status=HTTP_400_BAD_REQUEST
            )

        phone_service = CompanyPhoneService()
        phones = phone_service.get_phone_numbers_by_company(company_id)
        
        # Serialize phone numbers
        phone_data = [
            {
                "id": str(phone.id),
                "phone_number": str(phone.phone_number),
                "sid": phone.sid,
                "account_sid": phone.account_sid,
                "voice_url": phone.voice_url,
            }
            for phone in phones
        ]
        return Response(phone_data, status=HTTP_200_OK)

class DeleteCompanyPhone(BaseAPI):
    """
    Delete a phone number for a company.
    """
    def delete(self, request, *args, **kwargs):
        company_id = self.kwargs.get("company_id")
        phone_number_id = self.kwargs.get("phone_number_id")
        user = self.get_user()

        if not user.has_company_access(company_id):
            return Response(
                {"detail": "You don't have access to this company"},
                status=HTTP_400_BAD_REQUEST
            )

        phone_service = CompanyPhoneService()
        try:
            phone_service.delete_phone_number(phone_number_id)
            return Response(status=HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=HTTP_404_NOT_FOUND)