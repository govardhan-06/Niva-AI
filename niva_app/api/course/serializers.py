from rest_framework import serializers


class CreateCourseInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(default=True)
    passing_score = serializers.DecimalField(max_digits=5, decimal_places=2, default=60.00)
    max_score = serializers.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    syllabus = serializers.CharField(required=False, allow_blank=True)
    instructions = serializers.CharField(required=False, allow_blank=True)
    evaluation_criteria = serializers.CharField(required=False, allow_blank=True)


class GetCourseInputSerializer(serializers.Serializer):
    course_id = serializers.UUIDField()


class GetAllCoursesInputSerializer(serializers.Serializer):
    is_active = serializers.BooleanField(required=False)


class UpdateCourseInputSerializer(serializers.Serializer):
    course_id = serializers.UUIDField()
    name = serializers.CharField(max_length=150, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    passing_score = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    max_score = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    syllabus = serializers.CharField(required=False, allow_blank=True)
    instructions = serializers.CharField(required=False, allow_blank=True)
    evaluation_criteria = serializers.CharField(required=False, allow_blank=True)


class DeleteCourseInputSerializer(serializers.Serializer):
    course_id = serializers.UUIDField()