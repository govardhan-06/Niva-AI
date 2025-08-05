from rest_framework import serializers
from custard_app.models import User, RoleType, Role, UserStatus

class CurrentUserDetailOutputSerializer(serializers.ModelSerializer):
    role_type = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "is_email_verified",
            "phone_number",
            "role_type",
            "company_name",
        ]

    def get_role_type(self, obj):
        return obj.role.role_type if obj.role else None

    def get_company_name(self, obj):
        return obj.company.name if obj.company else None

class UserCreateSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text="Email address for the new user")
    password = serializers.CharField(write_only=True, help_text="Password for the new user")
    role_type = serializers.ChoiceField(
        choices=RoleType.choices,
        help_text="Role type for the user (admin/user)"
    )
    first_name = serializers.CharField(required=False, help_text="User's first name")
    last_name = serializers.CharField(required=False, help_text="User's last name")
    phone_number = serializers.CharField(required=False, help_text="User's phone number")

class UserUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, help_text="User's email address")
    role_type = serializers.ChoiceField(
        choices=RoleType.choices,
        required=False,
        help_text="Role type for the user (admin/user)"
    )
    status = serializers.ChoiceField(
        choices=UserStatus.choices,
        required=False,
        help_text="User's status (active/inactive/blocked)"
    )
    first_name = serializers.CharField(required=False, help_text="User's first name")
    last_name = serializers.CharField(required=False, help_text="User's last name")
    phone_number = serializers.CharField(required=False, help_text="User's phone number")
    password = serializers.CharField(write_only=True, required=False, help_text="User's password")

class UserListSerializer(serializers.ModelSerializer):
    role_type = serializers.CharField(source='role.role_type')
    company_name = serializers.CharField(source='company.name')
    
    class Meta:
        model = User
        fields = [
            'id', 
            'email', 
            'first_name', 
            'last_name', 
            'phone_number', 
            'role_type',
            'company_name',
            'is_active', 
            'is_email_verified', 
            'created_at'
        ]