from rest_framework import status
from rest_framework.response import Response


def message_response(message, *, http_status=status.HTTP_200_OK, **extra):
    """
    Success envelope aligned with error shape: {"detail": "..."}.
    Extra keys (e.g. username) may be included alongside detail.
    """
    payload = {"detail": message, **extra}
    return Response(payload, status=http_status)
