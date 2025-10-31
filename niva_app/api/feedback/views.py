import logging
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from niva_app.api.common.views import BaseAPI
from niva_app.services.feedback import (
    get_feedback,
    get_student_feedbacks,
    get_feedbacks_by_user_id
)
from .serializers import (
    FeedbackOutputSerializer,
    GetFeedbackInputSerializer,
    GetStudentFeedbacksInputSerializer,
    GetFeedbacksByUserIdInputSerializer
)

logger = logging.getLogger(__name__)


class GetFeedback(BaseAPI):
    """
    Get Feedback API

    API to retrieve a specific feedback by ID.

    Request:
        feedback_id: UUID

    Response:
        message: string
        feedback: {
            id: UUID,
            student: UUID,
            student_name: string,
            daily_call: UUID,
            agent: UUID,
            agent_name: string,
            course_name: string,
            overall_rating: integer,
            communication_rating: integer,
            technical_rating: integer,
            confidence_rating: integer,
            average_rating: float,
            feedback_text: string,
            strengths: string,
            improvements: string,
            recommendations: string,
            created_at: datetime,
            updated_at: datetime
        }
    """
    query_params_serializer_class = GetFeedbackInputSerializer

    def get(self, request, *args, **kwargs):
        data = self.validate_query_params()
        feedback_id = data['feedback_id']

        feedback = get_feedback(feedback_id)
        if not feedback:
            return self.get_response_400("Feedback not found")

        serializer = FeedbackOutputSerializer(feedback)
        return self.get_response_200(
            message="Feedback retrieved successfully",
            feedback=serializer.data
        )


class GetStudentFeedbacks(BaseAPI):
    """
    Get Student Feedbacks API

    API to retrieve all feedbacks for a specific student and course.

    Request:
        student_id: string (required)
        course_id: string (required)
        limit: integer (optional, default: 10, max: 100)
        offset: integer (optional, default: 0)

    Response:
        message: string
        feedbacks: [
            {
                id: UUID,
                student: UUID,
                student_name: string,
                daily_call: UUID,
                agent: UUID,
                agent_name: string,
                course_name: string,
                overall_rating: integer,
                communication_rating: integer,
                technical_rating: integer,
                confidence_rating: integer,
                average_rating: float,
                feedback_text: string,
                strengths: string,
                improvements: string,
                recommendations: string,
                created_at: datetime,
                updated_at: datetime
            }
        ]
        total_count: integer
        limit: integer
        offset: integer
    """
    query_params_serializer_class = GetStudentFeedbacksInputSerializer

    def get(self, request, *args, **kwargs):
        data = self.validate_query_params()
        student_id = data['student_id']
        course_id = data['course_id']
        limit = data.get('limit', 10)
        offset = data.get('offset', 0)

        feedbacks, total_count = get_student_feedbacks(student_id, course_id, limit, offset)
        
        if not feedbacks and total_count == 0:
            return self.get_response_400("Student not found, course not found, student not enrolled in course, or no feedbacks available")

        serializer = FeedbackOutputSerializer(feedbacks, many=True)
        return self.get_response_200(
            message="Student feedbacks retrieved successfully",
            feedbacks=serializer.data,
            total_count=total_count,
            limit=limit,
            offset=offset
        )


class GetFeedbacksByUserId(BaseAPI):
    """
    Get Feedbacks by User ID API

    API to retrieve all feedbacks for the current user (or specified user_id).
    Each user is mapped to a student profile, so this retrieves feedbacks for that student.

    Request:
        user_id: string (optional, defaults to current authenticated user)
        course_id: string (optional, filter by course)
        limit: integer (optional, default: 10, max: 100)
        offset: integer (optional, default: 0)

    Response:
        message: string
        feedbacks: [
            {
                id: UUID,
                student: UUID,
                student_name: string,
                daily_call: UUID,
                agent: UUID,
                agent_name: string,
                course_name: string,
                overall_rating: integer,
                communication_rating: integer,
                technical_rating: integer,
                confidence_rating: integer,
                average_rating: float,
                feedback_text: string,
                strengths: string,
                improvements: string,
                recommendations: string,
                created_at: datetime,
                updated_at: datetime
            }
        ]
        total_count: integer
        limit: integer
        offset: integer
    """
    query_params_serializer_class = GetFeedbacksByUserIdInputSerializer

    def get(self, request, *args, **kwargs):
        data = self.validate_query_params()
        
        # Get user_id from query params or use current authenticated user
        user_id = data.get('user_id')
        if not user_id:
            # Default to current authenticated user
            user = self.get_user()
            user_id = str(user.id)
        
        course_id = data.get('course_id')
        limit = data.get('limit', 10)
        offset = data.get('offset', 0)

        feedbacks, total_count = get_feedbacks_by_user_id(user_id, course_id, limit, offset)
        
        if not feedbacks and total_count == 0:
            return self.get_response_400("No student profile found for this user or no feedbacks available")

        serializer = FeedbackOutputSerializer(feedbacks, many=True)
        return self.get_response_200(
            message="Feedbacks retrieved successfully",
            feedbacks=serializer.data,
            total_count=total_count,
            limit=limit,
            offset=offset
        )


