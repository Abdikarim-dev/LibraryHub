from django.db import connection
from django.http import JsonResponse
from django.views import View


class HealthCheckView(View):
    """Liveness/readiness: process up + database reachable."""

    authentication_classes = []  # unused for Django View
    permission_classes = []

    def get(self, request):
        try:
            connection.ensure_connection()
            db_ok = True
        except Exception:
            db_ok = False
        payload = {"status": "ok" if db_ok else "degraded", "database": db_ok}
        return JsonResponse(payload, status=200 if db_ok else 503)
