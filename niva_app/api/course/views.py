import logging
from django.core.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from niva_app.api.common.views import BaseAPI
from niva_app.services.course import (
    create_course,
    get_course,
    get_all_courses,
    update_course,
    delete_course,
    validate_course_data
)
from niva_app.models import Course
from .serializers import (
    CreateCourseInputSerializer,
    GetCourseInputSerializer,
    GetAllCoursesInputSerializer,
    UpdateCourseInputSerializer,
    DeleteCourseInputSerializer
)

logger = logging.getLogger(__name__)


class ListAllCourses(BaseAPI):
    """
    List All Courses API - Simple List
    
    GET endpoint to retrieve a simple list of all courses with id and name.
    This is a lightweight alternative to GetAllCourses for quick lookups.
    
    No request body required.
    
    Response:
        courses: [
            {
                id: UUID,
                name: string,
                description: string,
                is_active: boolean,
                language: string
            }
        ]
    """
    
    def get(self, request, *args, **kwargs):
        try:
            courses = Course.objects.all()
            
            courses_data = []
            for course in courses:
                courses_data.append({
                    "id": str(course.id),
                    "name": course.name,
                    "description": course.description,
                    "is_active": course.is_active,
                    "language": course.language
                })
            
            return Response(
                {"courses": courses_data},
                status=HTTP_200_OK,
            )
        
        except Exception as e:
            logger.error(f"Error listing courses: {str(e)}")
            return Response(
                data={"error": "Failed to list courses"},
                status=HTTP_400_BAD_REQUEST
            )


class CreateCourse(BaseAPI):
    """
    Create Course API

    API to create a new course and its associated agent.

    Request:
        name: string
        description: string (optional)
        is_active: boolean (default: true)
        passing_score: decimal (default: 60.00)
        max_score: decimal (default: 100.00)
        syllabus: string (optional)
        instructions: string (optional)
        evaluation_criteria: string (optional)
        language: string (optional, default: 'en')

    Response:
        message: string
        course: {
            id: UUID,
            name: string,
            description: string,
            is_active: boolean,
            passing_score: decimal,
            max_score: decimal,
            syllabus: string,
            instructions: string,
            evaluation_criteria: string,
            created_at: datetime,
            updated_at: datetime,
            agents: [
                {
                    id: UUID,
                    name: string,
                    is_active: boolean,
                    language: string,
                    agent_type: string
                }
            ]
        }
    """
    input_serializer_class = CreateCourseInputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()

        try:
            validate_course_data(data)

            course = create_course(
                name=data["name"],
                description=data.get("description", ""),
                is_active=data.get("is_active", True),
                passing_score=float(data.get("passing_score", 60.00)),
                max_score=float(data.get("max_score", 100.00)),
                syllabus=data.get("syllabus", ""),
                instructions=data.get("instructions", ""),
                evaluation_criteria=data.get("evaluation_criteria", ""),
                language=data.get("language", "en")
            )

            # Get associated agents
            agents_data = []
            for agent in course.agents.all():
                agents_data.append({
                    "id": str(agent.id),
                    "name": agent.name,
                    "is_active": agent.is_active,
                    "language": agent.language,
                    "agent_type": agent.agent_type
                })

            course_data = {
                "id": str(course.id),
                "name": course.name,
                "description": course.description,
                "is_active": course.is_active,
                "passing_score": str(course.passing_score),
                "max_score": str(course.max_score),
                "syllabus": course.syllabus,
                "instructions": course.instructions,
                "evaluation_criteria": course.evaluation_criteria,
                "language": course.language,
                "created_at": course.created_at.isoformat(),
                "updated_at": course.updated_at.isoformat(),
                "agents": agents_data,
            }

            return Response(
                {
                    "message": "Course and associated agent created successfully",
                    "course": course_data
                },
                status=HTTP_200_OK,
            )

        except ValidationError as e:
            logger.error("Validation Error: %s", str(e))
            return Response(data=e.message_dict, status=HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating course: {str(e)}")
            return Response(
                data={"error": "Failed to create course"},
                status=HTTP_400_BAD_REQUEST
            )


class GetCourse(BaseAPI):
    """
    Get Course API

    API to get a specific course by ID.

    Request:
        course_id: UUID

    Response:
        course: {
            id: UUID,
            name: string,
            description: string,
            is_active: boolean,
            passing_score: decimal,
            max_score: decimal,
            syllabus: string,
            instructions: string,
            evaluation_criteria: string,
            created_at: datetime,
            updated_at: datetime
        }
    """
    input_serializer_class = GetCourseInputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()

        try:
            course = get_course(str(data["course_id"]))
            
            if not course:
                return Response(
                    data={"error": "Course not found"},
                    status=HTTP_404_NOT_FOUND
                )

            # Get associated agents
            agents_data = []
            for agent in course.agents.all():
                agents_data.append({
                    "id": str(agent.id),
                    "name": agent.name,
                    "is_active": agent.is_active,
                    "language": agent.language,
                    "agent_type": agent.agent_type
                })

            course_data = {
                "id": str(course.id),
                "name": course.name,
                "description": course.description,
                "is_active": course.is_active,
                "passing_score": str(course.passing_score),
                "max_score": str(course.max_score),
                "syllabus": course.syllabus,
                "instructions": course.instructions,
                "evaluation_criteria": course.evaluation_criteria,
                "language": course.language,
                "created_at": course.created_at.isoformat(),
                "updated_at": course.updated_at.isoformat(),
                "agents": agents_data,
            }

            return Response(
                {"course": course_data},
                status=HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error getting course: {str(e)}")
            return Response(
                data={"error": "Failed to get course"},
                status=HTTP_400_BAD_REQUEST
            )


class GetAllCourses(BaseAPI):
    """
    Get All Courses API

    API to get all courses with optional filtering.

    Request:
        is_active: boolean (optional)

    Response:
        courses: [
            {
                id: UUID,
                name: string,
                description: string,
                is_active: boolean,
                passing_score: decimal,
                max_score: decimal,
                syllabus: string,
                instructions: string,
                evaluation_criteria: string,
                created_at: datetime,
                updated_at: datetime
            }
        ]
    """
    input_serializer_class = GetAllCoursesInputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()

        try:
            courses = get_all_courses(is_active=data.get("is_active"))
            
            courses_data = []
            for course in courses:
                # Get associated agents for each course
                agents_data = []
                for agent in course.agents.all():
                    agents_data.append({
                        "id": str(agent.id),
                        "name": agent.name,
                        "is_active": agent.is_active,
                        "language": agent.language,
                        "agent_type": agent.agent_type
                    })
                
                courses_data.append({
                    "id": str(course.id),
                    "name": course.name,
                    "description": course.description,
                    "is_active": course.is_active,
                    "passing_score": str(course.passing_score),
                    "max_score": str(course.max_score),
                    "syllabus": course.syllabus,
                    "instructions": course.instructions,
                    "evaluation_criteria": course.evaluation_criteria,
                    "language": course.language,
                    "created_at": course.created_at.isoformat(),
                    "updated_at": course.updated_at.isoformat(),
                    "agents": agents_data,
                })

            return Response(
                {"courses": courses_data},
                status=HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error getting courses: {str(e)}")
            return Response(
                data={"error": "Failed to get courses"},
                status=HTTP_400_BAD_REQUEST
            )


class UpdateCourse(BaseAPI):
    """
    Update Course API

    API to update an existing course.

    Request:
        course_id: UUID
        name: string (optional)
        description: string (optional)
        is_active: boolean (optional)
        passing_score: decimal (optional)
        max_score: decimal (optional)
        syllabus: string (optional)
        instructions: string (optional)
        evaluation_criteria: string (optional)

    Response:
        message: string
        course: {
            id: UUID,
            name: string,
            description: string,
            is_active: boolean,
            passing_score: decimal,
            max_score: decimal,
            syllabus: string,
            instructions: string,
            evaluation_criteria: string,
            created_at: datetime,
            updated_at: datetime
        }
    """
    input_serializer_class = UpdateCourseInputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()

        try:
            validate_course_data(data)

            course = update_course(
                course_id=str(data["course_id"]),
                name=data.get("name"),
                description=data.get("description"),
                is_active=data.get("is_active"),
                passing_score=float(data["passing_score"]) if data.get("passing_score") else None,
                max_score=float(data["max_score"]) if data.get("max_score") else None,
                syllabus=data.get("syllabus"),
                instructions=data.get("instructions"),
                evaluation_criteria=data.get("evaluation_criteria"),
                language=data.get("language")
            )

            if not course:
                return Response(
                    data={"error": "Course not found"},
                    status=HTTP_404_NOT_FOUND
                )

            course_data = {
                "id": str(course.id),
                "name": course.name,
                "description": course.description,
                "is_active": course.is_active,
                "passing_score": str(course.passing_score),
                "max_score": str(course.max_score),
                "syllabus": course.syllabus,
                "instructions": course.instructions,
                "evaluation_criteria": course.evaluation_criteria,
                "language": course.language,
                "created_at": course.created_at.isoformat(),
                "updated_at": course.updated_at.isoformat(),
            }

            return Response(
                {
                    "message": "Course updated successfully",
                    "course": course_data
                },
                status=HTTP_200_OK,
            )

        except ValidationError as e:
            logger.error("Validation Error: %s", str(e))
            return Response(data=e.message_dict, status=HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error updating course: {str(e)}")
            return Response(
                data={"error": "Failed to update course"},
                status=HTTP_400_BAD_REQUEST
            )


class DeleteCourse(BaseAPI):
    """
    Delete Course API

    API to delete a course.

    Request:
        course_id: UUID

    Response:
        message: string
    """
    input_serializer_class = DeleteCourseInputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()

        try:
            deleted = delete_course(str(data["course_id"]))
            
            if not deleted:
                return Response(
                    data={"error": "Course not found"},
                    status=HTTP_404_NOT_FOUND
                )

            return Response(
                {"message": "Course deleted successfully"},
                status=HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error deleting course: {str(e)}")
            return Response(
                data={"error": "Failed to delete course"},
                status=HTTP_400_BAD_REQUEST
            )