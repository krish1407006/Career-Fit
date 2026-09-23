from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def health(request):
    """Lightweight liveness probe that also checks the database."""
    db_ok = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        db_ok = False
    return JsonResponse({"status": "ok" if db_ok else "degraded", "database": db_ok})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/resumes/", include("apps.resumes.urls")),
    path("api/", include("apps.jobs.urls")),
    path("api/", include("apps.assessments.urls")),
    path("api/", include("apps.interviews.urls")),
    path("api/", include("apps.dashboard.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)