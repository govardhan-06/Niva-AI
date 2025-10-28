import logging
from django.core.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from niva_app.api.common.views import BaseAPI
from niva_app.services.student import (
    create_student,
    get_student,
    get_all_students,
    update_student,
    delete_student,
    validate_student_data,
    associate_user_with_student,
    get_student_by_user_id
)
from niva_app.models import Student
from .serializers import (
    CreateStudentInputSerializer,
    GetStudentInputSerializer,
    GetAllStudentsInputSerializer,
    UpdateStudentInputSerializer,
    DeleteStudentInputSerializer,
    AssociateUserWithStudentInputSerializer,
    GetStudentByUserInputSerializer
)

logger = logging.getLogger(__name__)


class ListAllStudents(BaseAPI):
    """
    List All Students API - Simple List
    
    GET endpoint to retrieve a simple list of all students with id and name.
    This is a lightweight alternative to GetAllStudents for quick lookups.
    
    No request body required.
    
    Response:
        students: [
            {
                id: UUID,
                first_name: string,
                last_name: string,
                full_name: string
            }
        ]
    """
    
    def get(self, request, *args, **kwargs):
        try:
            students = Student.objects.all()
            
            students_data = []
            for student in students:
                students_data.append({
                    "id": str(student.id),
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "full_name": f"{student.first_name} {student.last_name}".strip()
                })
            
            return Response(
                {"students": students_data},
                status=HTTP_200_OK,
            )
        
        except Exception as e:
            logger.error(f"Error listing students: {str(e)}")
            return Response(
                data={"error": "Failed to list students"},
                status=HTTP_400_BAD_REQUEST
            )


class CreateStudent(BaseAPI):
    """
    Create Student API

    API to create a new student and optionally associate with courses.

    Request:
        first_name: string (required)
        last_name: string (optional)
        gender: string (optional, default: 'UNKNOWN')
        date_of_birth: date (optional)
        email: string (optional)
        phone_number: string (required)
        course_ids: array of UUIDs (optional)

    Response:
        message: string
        student: {
            id: UUID,
            first_name: string,
            last_name: string,
            gender: string,
            date_of_birth: date,
            email: string,
            phone_number: string,
            created_at: datetime,
            updated_at: datetime,
            courses: [
                {
                    id: UUID,
                    name: string,
                    description: string,
                    is_active: boolean,
                    language: string
                }
            ]
        }
    """
    input_serializer_class = CreateStudentInputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()

        try:
            validate_student_data(data)

            student = create_student(
                first_name=data["first_name"],
                last_name=data.get("last_name", ""),
                gender=data.get("gender", "UNKNOWN"),
                date_of_birth=data.get("date_of_birth"),
                email=data.get("email", ""),
                phone_number=data["phone_number"],
                course_ids=data.get("course_ids", [])
            )

            # Get associated courses
            courses_data = []
            for course in student.course.all():
                courses_data.append({
                    "id": str(course.id),
                    "name": course.name,
                    "description": course.description,
                    "is_active": course.is_active,
                    "language": course.language
                })

            student_data = {
                "id": str(student.id),
                "first_name": student.first_name,
                "last_name": student.last_name,
                "gender": student.gender,
                "date_of_birth": student.date_of_birth.isoformat() if student.date_of_birth else None,
                "email": student.email,
                "phone_number": student.phone_number,
                "created_at": student.created_at.isoformat(),
                "updated_at": student.updated_at.isoformat(),
                "courses": courses_data,
            }

            return Response(
                {
                    "message": "Student created successfully",
                    "student": student_data
                },
                status=HTTP_200_OK,
            )

        except ValidationError as e:
            logger.error("Validation Error: %s", str(e))
            return Response(data={"error": str(e)}, status=HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating student: {str(e)}")
            return Response(
                data={"error": "Failed to create student"},
                status=HTTP_400_BAD_REQUEST
            )


class GetStudent(BaseAPI):
    """
    Get Student API

    API to get a specific student by ID.

    Request:
        student_id: UUID

    Response:
        student: {
            id: UUID,
            first_name: string,
            last_name: string,
            gender: string,
            date_of_birth: date,
            email: string,
            phone_number: string,
            created_at: datetime,
            updated_at: datetime,
            courses: [
                {
                    id: UUID,
                    name: string,
                    description: string,
                    is_active: boolean,
                    language: string
                }
            ]
        }
    """
    input_serializer_class = GetStudentInputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()

        try:
            student = get_student(str(data["student_id"]))
            
            if not student:
                return Response(
                    data={"error": "Student not found"},
                    status=HTTP_404_NOT_FOUND
                )

            # Get associated courses
            courses_data = []
            for course in student.course.all():
                courses_data.append({
                    "id": str(course.id),
                    "name": course.name,
                    "description": course.description,
                    "is_active": course.is_active,
                    "language": course.language
                })

            student_data = {
                "id": str(student.id),
                "first_name": student.first_name,
                "last_name": student.last_name,
                "gender": student.gender,
                "date_of_birth": student.date_of_birth.isoformat() if student.date_of_birth else None,
                "email": student.email,
                "phone_number": student.phone_number,
                "created_at": student.created_at.isoformat(),
                "updated_at": student.updated_at.isoformat(),
                "courses": courses_data,
            }

            return Response(
                {"student": student_data},
                status=HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error getting student: {str(e)}")
            return Response(
                data={"error": "Failed to get student"},
                status=HTTP_400_BAD_REQUEST
            )


class GetAllStudents(BaseAPI):
    """
    Get All Students API

    API to get all students with optional filtering.

    Request:
        course_id: UUID (optional)
        phone_number: string (optional)
        email: string (optional)

    Response:
        students: [
            {
                id: UUID,
                first_name: string,
                last_name: string,
                gender: string,
                date_of_birth: date,
                email: string,
                phone_number: string,
                created_at: datetime,
                updated_at: datetime,
                courses: [
                    {
                        id: UUID,
                        name: string,
                        description: string,
                        is_active: boolean,
                        language: string
                    }
                ]
            }
        ]
    """
    input_serializer_class = GetAllStudentsInputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()

        try:
            students = get_all_students(
                course_id=data.get("course_id"),
                phone_number=data.get("phone_number"),
                email=data.get("email")
            )
            
            students_data = []
            for student in students:
                # Get associated courses for each student
                courses_data = []
                for course in student.course.all():
                    courses_data.append({
                        "id": str(course.id),
                        "name": course.name,
                        "description": course.description,
                        "is_active": course.is_active,
                        "language": course.language
                    })
                
                students_data.append({
                    "id": str(student.id),
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "gender": student.gender,
                    "date_of_birth": student.date_of_birth.isoformat() if student.date_of_birth else None,
                    "email": student.email,
                    "phone_number": student.phone_number,
                    "created_at": student.created_at.isoformat(),
                    "updated_at": student.updated_at.isoformat(),
                    "courses": courses_data,
                })

            return Response(
                {"students": students_data},
                status=HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error getting students: {str(e)}")
            return Response(
                data={"error": "Failed to get students"},
                status=HTTP_400_BAD_REQUEST
            )


class UpdateStudent(BaseAPI):
    """
    Update Student API

    API to update an existing student.

    Request:
        student_id: UUID
        first_name: string (optional)
        last_name: string (optional)
        gender: string (optional)
        date_of_birth: date (optional)
        email: string (optional)
        phone_number: string (optional)
        course_ids: array of UUIDs (optional)

    Response:
        message: string
        student: {
            id: UUID,
            first_name: string,
            last_name: string,
            gender: string,
            date_of_birth: date,
            email: string,
            phone_number: string,
            created_at: datetime,
            updated_at: datetime,
            courses: [
                {
                    id: UUID,
                    name: string,
                    description: string,
                    is_active: boolean,
                    language: string
                }
            ]
        }
    """
    input_serializer_class = UpdateStudentInputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()

        try:
            validate_student_data(data)

            student = update_student(
                student_id=str(data["student_id"]),
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                gender=data.get("gender"),
                date_of_birth=data.get("date_of_birth"),
                email=data.get("email"),
                phone_number=data.get("phone_number"),
                course_ids=data.get("course_ids")
            )

            if not student:
                return Response(
                    data={"error": "Student not found"},
                    status=HTTP_404_NOT_FOUND
                )

            # Get associated courses
            courses_data = []
            for course in student.course.all():
                courses_data.append({
                    "id": str(course.id),
                    "name": course.name,
                    "description": course.description,
                    "is_active": course.is_active,
                    "language": course.language
                })

            student_data = {
                "id": str(student.id),
                "first_name": student.first_name,
                "last_name": student.last_name,
                "gender": student.gender,
                "date_of_birth": student.date_of_birth.isoformat() if student.date_of_birth else None,
                "email": student.email,
                "phone_number": student.phone_number,
                "created_at": student.created_at.isoformat(),
                "updated_at": student.updated_at.isoformat(),
                "courses": courses_data,
            }

            return Response(
                {
                    "message": "Student updated successfully",
                    "student": student_data
                },
                status=HTTP_200_OK,
            )

        except ValidationError as e:
            logger.error("Validation Error: %s", str(e))
            return Response(data={"error": str(e)}, status=HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error updating student: {str(e)}")
            return Response(
                data={"error": "Failed to update student"},
                status=HTTP_400_BAD_REQUEST
            )


class DeleteStudent(BaseAPI):
    """
    Delete Student API

    API to delete a student.

    Request:
        student_id: UUID

    Response:
        message: string
    """
    input_serializer_class = DeleteStudentInputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()

        try:
            deleted = delete_student(str(data["student_id"]))
            
            if not deleted:
                return Response(
                    data={"error": "Student not found"},
                    status=HTTP_404_NOT_FOUND
                )

            return Response(
                {"message": "Student deleted successfully"},
                status=HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error deleting student: {str(e)}")
            return Response(
                data={"error": "Failed to delete student"},
                status=HTTP_400_BAD_REQUEST
            )

class AssociateUserWithStudent(BaseAPI):
    """
    Associate User with Student API

    API to associate an existing user account with an existing student profile.

    Request:
        user_id: UUID (required)
        student_id: UUID (required)

    Response:
        message: string
        student: {
            id: UUID,
            first_name: string,
            last_name: string,
            email: string,
            phone_number: string,
            user_id: UUID
        }
    """
    input_serializer_class = AssociateUserWithStudentInputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()

        try:
            student = associate_user_with_student(
                user_id=str(data["user_id"]),
                student_id=str(data["student_id"])
            )

            student_data = {
                "id": str(student.id),
                "first_name": student.first_name,
                "last_name": student.last_name,
                "email": student.email,
                "phone_number": student.phone_number,
                "user_id": str(student.user.id) if student.user else None
            }

            return Response(
                {
                    "message": "User associated with student successfully",
                    "student": student_data
                },
                status=HTTP_200_OK,
            )

        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return Response(
                data={"error": str(e)},
                status=HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error associating user with student: {str(e)}")
            return Response(
                data={"error": "Failed to associate user with student"},
                status=HTTP_400_BAD_REQUEST
            )


class GetStudentByUser(BaseAPI):
    """
    Get Student by User API

    API to get a student profile by user ID.

    Request:
        user_id: UUID

    Response:
        student: {
            id: UUID,
            first_name: string,
            last_name: string,
            gender: string,
            date_of_birth: date,
            email: string,
            phone_number: string,
            user_id: UUID,
            courses: [...]
        }
    """
    input_serializer_class = GetStudentByUserInputSerializer

    def post(self, request, *args, **kwargs):
        data = self.validate_input_data()

        try:
            student = get_student_by_user_id(str(data["user_id"]))
            
            if not student:
                return Response(
                    data={"error": "No student profile found for this user"},
                    status=HTTP_404_NOT_FOUND
                )

            # Get associated courses
            courses_data = []
            for course in student.course.all():
                courses_data.append({
                    "id": str(course.id),
                    "name": course.name,
                    "description": course.description,
                    "is_active": course.is_active,
                    "language": course.language
                })

            student_data = {
                "id": str(student.id),
                "first_name": student.first_name,
                "last_name": student.last_name,
                "gender": student.gender,
                "date_of_birth": student.date_of_birth.isoformat() if student.date_of_birth else None,
                "email": student.email,
                "phone_number": student.phone_number,
                "user_id": str(student.user.id) if student.user else None,
                "created_at": student.created_at.isoformat(),
                "updated_at": student.updated_at.isoformat(),
                "courses": courses_data,
            }

            return Response(
                {"student": student_data},
                status=HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error getting student by user: {str(e)}")
            return Response(
                data={"error": "Failed to get student profile"},
                status=HTTP_400_BAD_REQUEST
            )
