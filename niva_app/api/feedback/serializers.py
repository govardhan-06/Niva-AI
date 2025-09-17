from rest_framework import serializers
from niva_app.models.feedback import Feedback
from niva_app.models.students import Student
from niva_app.models.dailycalls import DailyCall
from niva_app.models.agents import Agent


class FeedbackOutputSerializer(serializers.ModelSerializer):
    """Serializer for feedback output data"""
    
    student_name = serializers.SerializerMethodField()
    agent_name = serializers.SerializerMethodField()
    course_name = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = Feedback
        fields = [
            'id',
            'student',
            'student_name',
            'daily_call',
            'agent',
            'agent_name',
            'course_name',
            'overall_rating',
            'communication_rating',
            'technical_rating',
            'confidence_rating',
            'average_rating',
            'feedback_text',
            'strengths',
            'improvements',
            'recommendations',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"
    
    def get_agent_name(self, obj):
        return obj.agent.name
    
    def get_course_name(self, obj):
        # Get course name from the student's course relationship
        courses = obj.student.course.all()
        if courses.exists():
            return courses.first().name
        return None
    
    def get_average_rating(self, obj):
        return obj.get_average_rating()


class GetFeedbackInputSerializer(serializers.Serializer):
    """Serializer for getting a specific feedback"""
    feedback_id = serializers.CharField()


class GetStudentFeedbacksInputSerializer(serializers.Serializer):
    """Serializer for getting all feedbacks for a specific student and course"""
    student_id = serializers.CharField()
    course_id = serializers.CharField()
    limit = serializers.IntegerField(required=False, min_value=1, max_value=100, default=10)
    offset = serializers.IntegerField(required=False, min_value=0, default=0)


