from django.shortcuts import get_object_or_404
from django.db import models
from django.db.models import Sum, Count
from django.db.models.functions import Length
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.status import HTTP_200_OK

from custard_app.models import Memory, Company, Agent, WebsiteSource, Document
from custard_app.services.agent_memory import MemoryService
from custard_app.api.common.views import BaseAPI
from app.config import GCP_BUCKET_URL
import threading
import logging

logger = logging.getLogger(__name__)

class AddMemory(BaseAPI):
    class InputSerializer(serializers.Serializer):
        type = serializers.ChoiceField(
            choices=[("document", "document"), ("website", "website")]
        )
        url = serializers.CharField()
        name = serializers.CharField(required=True) 

    input_serializer_class = InputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()
        company_id = self.kwargs.get("company_id")
        company = Company.objects.get(id=company_id)

        if company.id != self.get_user().company.id:
            self.set_response_message("You are not allowed to edit this agent")
            return self.get_response_400()

        memory_service = MemoryService(company)

        memory_service.add_memory(
            memory_type=data["type"],
            url=data["url"],
            name=data["name"] 
        )

        return Response(
            status=HTTP_200_OK,
        )

class MemoryList(BaseAPI):
    def get(self, request, *args, **kwargs):
        user = self.get_user()
        company_id = self.kwargs.get("company_id")

        # Check company access
        if not user.has_company_access(company_id):
            return Response(
                {"detail": "You don't have access to this company"},
                status=status.HTTP_403_FORBIDDEN
            )

        memories = Memory.objects.filter(
            company_id=company_id
        ).order_by('-created_at')

        paginator = LimitOffsetPagination()
        paginated_memories = paginator.paginate_queryset(memories, request)

        serializer = MemoryOutputSerializer(paginated_memories, many=True)
        
        return paginator.get_paginated_response(serializer.data)

class MemoryDelete(BaseAPI):
    def delete(self, request, *args, **kwargs):
        user = self.get_user()
        memory_id = kwargs.get("memory_id")

        memory = get_object_or_404(Memory, id=memory_id)

        # Check company access
        if not user.has_company_access(memory.company_id):
            return Response(
                {"detail": "You don't have access to this memory"},
                status=status.HTTP_403_FORBIDDEN
            )

        memory.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class MemoryContent(BaseAPI):
    def get(self, request, *args, **kwargs):
        user = self.get_user()
        memory_id = self.kwargs.get("memory_id")
        
        # Get memory and check access
        memory = get_object_or_404(Memory, id=memory_id)
        
        if not user.has_company_access(memory.company_id):
            return Response(
                {"detail": "You don't have access to this memory"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get content based on memory type
        if memory.type == "document":
            # Get document chunks
            documents = Document.objects.filter(memory=memory).order_by('created_at')
            content_data = [
                {
                    "content": doc.content,
                    "chunk_index": idx,
                    "created_at": doc.created_at
                }
                for idx, doc in enumerate(documents)
            ]
        elif memory.type == "website":
            # Get website content chunks
            website_sources = WebsiteSource.objects.filter(
                company=memory.company,
                url=memory.url
            ).order_by('created_at')
            content_data = [
                {
                    "content": source.contents,
                    "chunk_index": idx,
                    "created_at": source.created_at
                }
                for idx, source in enumerate(website_sources)
            ]
        else:
            content_data = []
        
        # Paginate the content
        paginator = LimitOffsetPagination()
        paginated_content = paginator.paginate_queryset(content_data, request)
        
        return paginator.get_paginated_response(paginated_content)

class MemorySummary(BaseAPI):
    def get(self, request, *args, **kwargs):
        user = self.get_user()
        memory_id = self.kwargs.get("memory_id")
        
        # Get memory and check access
        memory = get_object_or_404(Memory, id=memory_id)
        
        if not user.has_company_access(memory.company_id):
            return Response(
                {"detail": "You don't have access to this memory"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get summary data based on memory type
        if memory.type == "document":
            document_count = Document.objects.filter(memory=memory).count()
            total_content_length = Document.objects.filter(memory=memory).aggregate(
                total_length=Sum(Length('content'))
            )['total_length'] or 0
            
            # Get a preview of the first chunk
            first_document = Document.objects.filter(memory=memory).first()
            preview = first_document.content[:500] + "..." if first_document and len(first_document.content) > 500 else (first_document.content if first_document else "")
            
        elif memory.type == "website":
            document_count = WebsiteSource.objects.filter(
                company=memory.company,
                url=memory.url
            ).count()
            
            total_content_length = WebsiteSource.objects.filter(
                company=memory.company,
                url=memory.url
            ).aggregate(
                total_length=Sum(Length('contents'))
            )['total_length'] or 0
            
            # Get a preview of the first chunk
            first_source = WebsiteSource.objects.filter(
                company=memory.company,
                url=memory.url
            ).first()
            preview = first_source.contents[:500] + "..." if first_source and len(first_source.contents) > 500 else (first_source.contents if first_source else "")
            
        else:
            document_count = 0
            total_content_length = 0
            preview = ""
        
        summary_data = {
            "memory_id": memory.id,
            "name": memory.name,
            "type": memory.type,
            "url": memory.url,
            "chunk_count": document_count,
            "total_content_length": total_content_length,
            "preview": preview,
            "created_at": memory.created_at,
            "updated_at": memory.updated_at
        }
        
        return Response(summary_data, status=status.HTTP_200_OK)

class MemoryContentSerializer(serializers.Serializer):
    content = serializers.CharField()
    chunk_index = serializers.IntegerField()
    created_at = serializers.DateTimeField()

class MemoryOutputSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Memory
        fields = ["id", "name", "file_url", "type", "url", "created_at"]

    def get_file_url(self, obj):
        if obj.type == "document":
            return GCP_BUCKET_URL + "/" + obj.url
        return obj.url