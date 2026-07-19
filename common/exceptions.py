from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class InventoryIntegrityError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Inventory inconsistency detected."
    default_code = "inventory_integrity"


def api_exception_handler(exc, context):
    """
    Normalize DRF errors to a consistent envelope:

      {"detail": "..."} or {"field": ["..."], ...}
    """
    response = exception_handler(exc, context)
    if response is None:
        return response

    data = response.data
    if isinstance(data, dict) and "error" in data and "detail" not in data:
        response.data = {"detail": data["error"]}
    elif isinstance(data, list):
        response.data = {"detail": data}
    elif isinstance(data, str):
        response.data = {"detail": data}
    return response
