from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from niva_app import urls as niva_urls
from pipecat_agents import urls as pipecat_urls

urlpatterns = static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include(niva_urls.auth_routes)),
    path("api/v1/company/", include(niva_urls.company_routes)),
    path("api/v1/agent/", include(niva_urls.agent_routes)),
    path("api/v1/agent-memory/", include(niva_urls.agent_memory_routes)),
    path("api/v1/daily/", include(niva_urls.daily_routes)),
    path("api/v1/pipecat/", include(pipecat_urls.agent_routes)),
]
