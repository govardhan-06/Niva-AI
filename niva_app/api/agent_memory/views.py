from django.shortcuts import get_object_or_404
from django.db import models
from django.db.models import Sum, Count
from django.db.models.functions import Length
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.status import HTTP_200_OK
from rest_framework.parsers import MultiPartParser, FormParser

from niva_app.models import Memory, Course, Agent, Document
from niva_app.services.agent_memory import MemoryService
from niva_app.api.common.views import BaseAPI
import threading
import logging

logger = logging.getLogger(__name__)

class AddMemory(BaseAPI):
    parser_classes = [MultiPartParser, FormParser]
    
    class InputSerializer(serializers.Serializer):
        type = serializers.ChoiceField(
            choices=[("document", "document"), ("website", "website")]
        )
        url = serializers.CharField(required=False)
        name = serializers.CharField(required=True)
        file = serializers.FileField(required=False)

    input_serializer_class = InputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()
        course_id = self.kwargs.get("course_id")
        course = Course.objects.get(id=course_id)

        # Check if user has access to this course
        if not course.is_active:
            self.set_response_message("This course is not active")
            return self.get_response_400()

        memory_service = MemoryService(course)

        if data["type"] == "document":
            # Handle file upload
            file = data.get("file")
            if not file:
                return Response(
                    {"error": "File is required for document type"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                # Upload file to local storage
                file_path = memory_service.upload_file(file, data["name"])
                
                # Add memory with local file path
                memory_service.add_memory(
                    memory_type=data["type"],
                    url=file_path,
                    name=data["name"] 
                )
                
                return Response(
                    {
                        "message": "Document uploaded and processed successfully",
                        "file_path": file_path
                    },
                    status=HTTP_200_OK,
                )
                
            except Exception as e:
                logger.error(f"Error processing file upload: {e}")
                return Response(
                    {"error": f"Failed to process file: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        elif data["type"] == "website":
            # Handle website URL
            url = data.get("url")
            if not url:
                return Response(
                    {"error": "URL is required for website type"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                memory_service.add_memory(
                    memory_type=data["type"],
                    url=url,
                    name=data["name"] 
                )
                
                return Response(
                    {"message": "Website memory added successfully"},
                    status=HTTP_200_OK,
                )
                
            except Exception as e:
                logger.error(f"Error adding website memory: {e}")
                return Response(
                    {"error": f"Failed to add website memory: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Fallback return (should not reach here)
        return Response(
            {"error": "Invalid memory type"},
            status=status.HTTP_400_BAD_REQUEST
        )

class UploadDocument(BaseAPI):
    """
    Separate endpoint for document uploads
    """
    parser_classes = [MultiPartParser, FormParser]
    
    class InputSerializer(serializers.Serializer):
        file = serializers.FileField()
        name = serializers.CharField()
    
    input_serializer_class = InputSerializer
    
    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()
        course_id = self.kwargs.get("course_id")
        course = Course.objects.get(id=course_id)

        if not course.is_active:
            self.set_response_message("This course is not active")
            return self.get_response_400()

        memory_service = MemoryService(course)
        
        try:
            file = data["file"]
            name = data["name"]
            
            # Upload file to local storage
            file_path = memory_service.upload_file(file, name)
            
            # Add memory with local file path
            memory_service.add_memory(
                memory_type="document",
                url=file_path,
                name=name
            )
            
            return Response(
                {
                    "message": "Document uploaded and processed successfully",
                    "file_path": file_path,
                    "name": name
                },
                status=HTTP_200_OK,
            )
            
        except Exception as e:
            logger.error(f"Error uploading document: {e}")
            return Response(
                {"error": f"Failed to upload document: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

class MemoryDelete(BaseAPI):
    def delete(self, request, *args, **kwargs):
        user = self.get_user()
        memory_id = kwargs.get("memory_id")

        memory = get_object_or_404(Memory, id=memory_id)

        # Check course access (implement course access logic as needed)
        # For now, allowing any authenticated user to delete
        # You may want to add course-specific permissions here

        memory.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class MemoryContent(BaseAPI):
    def get(self, request, *args, **kwargs):
        user = self.get_user()
        memory_id = self.kwargs.get("memory_id")
        
        # Get memory and check access
        memory = get_object_or_404(Memory, id=memory_id)
        
        # Check if course is active (you may add more specific access control)
        if not memory.course.is_active:
            return Response(
                {"detail": "This course is not active"},
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
        
        # Check if course is active
        if not memory.course.is_active:
            return Response(
                {"detail": "This course is not active"},
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
            
        else:
            document_count = 0
            total_content_length = 0
            preview = ""
        
        summary_data = {
            "memory_id": memory.id,
            "name": memory.name,
            "type": memory.type,
            "url": memory.url,
            "course_id": memory.course.id,
            "course_name": memory.course.name,
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
    course_name = serializers.CharField(source='course.name', read_only=True)

    class Meta:
        model = Memory
        fields = ["id", "name", "file_url", "type", "url", "course_name", "created_at"]

    def get_file_url(self, obj):
        if obj.type == "document":
            # Return local file URL
            from niva_app.services.local_storage import LocalStorageService
            storage_service = LocalStorageService()
            return storage_service.get_file_url(obj.url)
        return obj.url