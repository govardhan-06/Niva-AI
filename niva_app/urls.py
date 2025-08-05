from django.urls import path
from uuid import UUID

from custard_app.api.authentication.views import (
    CreateUser,
    ActivateUser,
    LoginView,
)

from custard_app.api.company.views import (
    CreateCompany,
    GetCompany,
    GetCompanyByName,
    UpdateCompany,
    AddCompanyPhone,
    UpdateCompanyPhone,
    ListCompanyPhones,
    DeleteCompanyPhone
)

from custard_app.api.agents.views import (
    CreateAgent,
    GetAgent,
    UpdateAgent,
    ListAgents,
    DisableAgent,
    CallProcessorStatus,
    ProcessPostCallDataView,
)

from custard_app.api.flows.views import (
    ListFlows,
    GetFlow,
    CreateFlow,
    UpdateFlow,
    GetFlowByVersion,
    RevertFlowVersion,
)

from custard_app.api.agent_memory.views import (
    AddMemory,
    MemoryList,
    MemoryDelete,
    MemoryContent,
    MemorySummary,
)

from custard_app.api.daily.views import (
    DailyWebhookView,
    DailyCallRecordingView,
    DailyRoomAPIView,
    CreateAndSaveRoomAPIView,
)

from custard_app.api.twilio.views import (
    TwilioVoiceWebhook,
    InitiateOutboundCall,
    # outbound_call_twiml,
    # call_status_webhook,
)

from custard_app.api.tests.views import (
    test_voice_call,
    test_health_check,
    test_active_calls,
    test_stop_call,
)

# Authentication routes
auth_routes = [
    path("register/", CreateUser.as_view(), name="register"),
    path("activate-user/", ActivateUser.as_view(), name="activate-user"),
    path("login/", LoginView.as_view(), name="login"),
]

# Company routes
company_routes = [
    path("create-company/", CreateCompany.as_view(), name="create-company"),
    path("<uuid:company_id>/", GetCompany.as_view(), name="get-company"),
    path("by-name/", GetCompanyByName.as_view(), name="get-company-by-name"),
    path("<uuid:company_id>/update/", UpdateCompany.as_view(), name="update-company"),
    path("<uuid:company_id>/add-phone/", AddCompanyPhone.as_view(), name="add-company-phone"),
    path("<uuid:company_id>/update-phone/", UpdateCompanyPhone.as_view(), name="update-company-phone"),
    path("<uuid:company_id>/phones/", ListCompanyPhones.as_view(), name="list-company-phones"),
    path("<uuid:company_id>/phones/<uuid:phone_number_id>/", DeleteCompanyPhone.as_view(), name="delete-company-phone"),
]

# Agent routes
agent_routes = [
    path("create/", CreateAgent.as_view(), name="create-agent"),
    path("<uuid:agent_id>/", GetAgent.as_view(), name="get-agent"),
    path("<uuid:agent_id>/update/", UpdateAgent.as_view(), name="update-agent"),
    path("<uuid:agent_id>/disable/", DisableAgent.as_view(), name="disable-agent"),
    path("list/", ListAgents.as_view(), name="list-agents"),
    path('process-post-call-data/', ProcessPostCallDataView.as_view(), name='process-post-call-data'),
    path('processor-status/', CallProcessorStatus.as_view(), name='call-processor-status'),
]

# Flow routes
flow_routes = [
    path("", ListFlows.as_view(), name="list-flows"),
    path("create/", CreateFlow.as_view(), name="create-flow"),
    path("<uuid:flow_id>/", GetFlow.as_view(), name="get-flow"),
    path("<uuid:flow_id>/update/", UpdateFlow.as_view(), name="update-flow"),
    path("<uuid:flow_id>/versions/<str:version_number>/", GetFlowByVersion.as_view(), name="get-flow-by-version"),
    path("<uuid:company_id>/revert/", RevertFlowVersion.as_view(), name="revert-flow-version"),
]

# Agent Memory routes
agent_memory_routes = [
    path('<uuid:company_id>/add-memory/', AddMemory.as_view(), name='add-memory'),
    path('<uuid:company_id>/list-memories/', MemoryList.as_view(), name='memory-list'),
    path('<uuid:company_id>/delete-memory/<uuid:memory_id>/', MemoryDelete.as_view(), name='delete-memory'),
    path('<uuid:company_id>/memory/<uuid:memory_id>/content/', MemoryContent.as_view(), name='memory-content'),
    path('<uuid:company_id>/memory/<uuid:memory_id>/summary/', MemorySummary.as_view(), name='memory-summary'),
]

# Daily API routes
daily_routes = [
    path("webhooks/daily/", DailyWebhookView.as_view(), name="daily-webhook"),
    path("calls/<uuid:daily_call_id>/recording/", DailyCallRecordingView.as_view(), name="daily-call-recording"),
    path("rooms/", DailyRoomAPIView.as_view(), name="create-daily-room"),
    path("rooms/create-and-save/", CreateAndSaveRoomAPIView.as_view(), name="create-and-save-daily-room"),
]

# Twilio API routes
twilio_routes = [
    path('voice-webhook/', TwilioVoiceWebhook.as_view(), name='twilio_voice_webhook'),
    path('initiate-call/', InitiateOutboundCall.as_view(), name='initiate_outbound_call'),
    # path('outbound-twiml/', outbound_call_twiml, name='outbound_call_twiml'),
    # path('status-webhook/', call_status_webhook, name='call_status_webhook'),
]

test_routes = [
    path('voice-call/', test_voice_call, name='test_voice_call'),
    path('health/', test_health_check, name='test_health_check'),
    path('active-calls/', test_active_calls, name='test_active_calls'),
    path('stop-call/', test_stop_call, name='test_stop_call'),
]                               