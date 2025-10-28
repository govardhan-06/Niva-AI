from rest_framework import serializers


class CreateStudentInputSerializer(serializers.Serializer):
    """
    Input Serializer for CreateStudent API

    This serializer is used to validate the input data for the CreateStudent API.
    """

    first_name = serializers.CharField(max_length=255, required=True)
    last_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    gender = serializers.ChoiceField(
        choices=[("MALE", "male"), ("FEMALE", "female"), ("RATHER_NOT_SAY", "rather not say"), ("UNKNOWN", "unknown")],
        required=False,
        default="UNKNOWN"
    )
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=20, required=True)
    course_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        help_text="List of course IDs to associate with the student"
    )


class GetStudentInputSerializer(serializers.Serializer):
    """
    Input Serializer for GetStudent API

    This serializer is used to validate the input data for the GetStudent API.
    """

    student_id = serializers.UUIDField()


class GetAllStudentsInputSerializer(serializers.Serializer):
    """
    Input Serializer for GetAllStudents API

    This serializer is used to validate the input data for the GetAllStudents API.
    """

    course_id = serializers.UUIDField(required=False)
    phone_number = serializers.CharField(max_length=20, required=False)
    email = serializers.EmailField(required=False)


class UpdateStudentInputSerializer(serializers.Serializer):
    """
    Input Serializer for UpdateStudent API

    This serializer is used to validate the input data for the UpdateStudent API.
    """

    student_id = serializers.UUIDField()
    first_name = serializers.CharField(max_length=255, required=False)
    last_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    gender = serializers.ChoiceField(
        choices=[("MALE", "male"), ("FEMALE", "female"), ("RATHER_NOT_SAY", "rather not say"), ("UNKNOWN", "unknown")],
        required=False
    )
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=20, required=False)
    course_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        help_text="List of course IDs to associate with the student"
    )


class DeleteStudentInputSerializer(serializers.Serializer):
    """
    Input Serializer for DeleteStudent API

    This serializer is used to validate the input data for the DeleteStudent API.
    """

    student_id = serializers.UUIDField()


class AssociateUserWithStudentInputSerializer(serializers.Serializer):
    """
    Input Serializer for AssociateUserWithStudent API

    This serializer is used to validate the input data for associating a user with a student.
    """

    user_id = serializers.UUIDField(required=True, help_text="User ID to associate")
    student_id = serializers.UUIDField(required=True, help_text="Student ID to associate")


class GetStudentByUserInputSerializer(serializers.Serializer):
    """
    Input Serializer for GetStudentByUser API

    This serializer is used to get a student by user ID.
    """

    user_id = serializers.UUIDField(required=True, help_text="User ID to look up")
