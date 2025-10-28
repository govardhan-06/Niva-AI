from django.urls import path
from uuid import UUID

from niva_app.api.authentication.views import (
    CreateUser,
    LoginView,
)

from niva_app.api.agents.views import (
    CallProcessorStatus,
    ProcessPostCallDataView,
)

from niva_app.api.agent_memory.views import (
    AddMemory,
    MemoryDelete,
    MemoryContent,
    MemorySummary,
)

from niva_app.api.daily.views import (
    DailyWebhookView,
    DailyCallRecordingView,
    DailyRoomAPIView,
    CreateAndSaveRoomAPIView,
)

from niva_app.api.tests.views import (
    test_voice_call,
    test_health_check,
    test_active_calls,
    test_stop_call,
)

from niva_app.api.entrypoint.views import (
    EntrypointVoiceAPI
)

from niva_app.api.course.views import (
    CreateCourse,
    GetCourse,
    GetAllCourses,
    UpdateCourse,
    DeleteCourse,
    ListAllCourses,
)

from niva_app.api.feedback.views import (
    GetFeedback,
    GetStudentFeedbacks,
)

from niva_app.api.student.views import (
    CreateStudent,
    GetStudent,
    GetAllStudents,
    UpdateStudent,
    DeleteStudent,
    ListAllStudents,
    AssociateUserWithStudent,
    GetStudentByUser,
)

# Authentication routes
auth_routes = [
    path("register/", CreateUser.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
]

# Agent routes
agent_routes = [
    path('process-post-call-data/', ProcessPostCallDataView.as_view(), name='process-post-call-data'),
    path('processor-status/', CallProcessorStatus.as_view(), name='call-processor-status'),
]

# Agent Memory routes
agent_memory_routes = [
    path('<uuid:course_id>/add-memory/', AddMemory.as_view(), name='add-memory'),
    path('<uuid:course_id>/delete-memory/<uuid:memory_id>/', MemoryDelete.as_view(), name='delete-memory'),
    path('<uuid:course_id>/memory/<uuid:memory_id>/content/', MemoryContent.as_view(), name='memory-content'),
    path('<uuid:course_id>/memory/<uuid:memory_id>/summary/', MemorySummary.as_view(), name='memory-summary'),
]

# Daily API routes
daily_routes = [
    path("webhooks/daily/", DailyWebhookView.as_view(), name="daily-webhook"),
    path("calls/<uuid:daily_call_id>/recording/", DailyCallRecordingView.as_view(), name="daily-call-recording"),
    path("rooms/", DailyRoomAPIView.as_view(), name="create-daily-room"),
    path("rooms/create-and-save/", CreateAndSaveRoomAPIView.as_view(), name="create-and-save-daily-room"),
]

#Test routes
test_routes = [
    path('voice-call/', test_voice_call, name='test_voice_call'),
    path('health/', test_health_check, name='test_health_check'),
    path('active-calls/', test_active_calls, name='test_active_calls'),
    path('stop-call/', test_stop_call, name='test_stop_call'),
]    

#Entrypoint routes
entrypoint_routes = [
    path('entrypoint/', EntrypointVoiceAPI.as_view(), name='entrypoint-api'),
]

# Course routes
course_routes = [
    path('create/', CreateCourse.as_view(), name='create-course'),
    path('get/', GetCourse.as_view(), name='get-course'),
    path('all/', GetAllCourses.as_view(), name='get-all-courses'),
    path('list/', ListAllCourses.as_view(), name='list-all-courses'),
    path('update/', UpdateCourse.as_view(), name='update-course'),
    path('delete/', DeleteCourse.as_view(), name='delete-course'),
]

# Feedback routes
feedback_routes = [
    path('get/', GetFeedback.as_view(), name='get-feedback'),
    path('student/', GetStudentFeedbacks.as_view(), name='get-student-feedbacks'),
]

# Student routes
student_routes = [
    path('create/', CreateStudent.as_view(), name='create-student'),
    path('get/', GetStudent.as_view(), name='get-student'),
    path('all/', GetAllStudents.as_view(), name='get-all-students'),
    path('list/', ListAllStudents.as_view(), name='list-all-students'),
    path('update/', UpdateStudent.as_view(), name='update-student'),
    path('delete/', DeleteStudent.as_view(), name='delete-student'),
    path('associate-user/', AssociateUserWithStudent.as_view(), name='associate-user-with-student'),
    path('get-by-user/', GetStudentByUser.as_view(), name='get-student-by-user'),
]