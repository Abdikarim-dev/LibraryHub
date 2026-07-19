from rest_framework.permissions import BasePermission

from users.models import User
from users.permissions import IsAdminOrLibrarian  # noqa: F401 — re-export


class IsStaffOrReadOwnBorrow(BasePermission):
    """List/retrieve: member sees own; staff sees all."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role in (User.Role.ADMIN, User.Role.LIBRARIAN):
            return True
        if hasattr(obj, "member_id"):
            return obj.member_id == user.pk
        if hasattr(obj, "borrow_record"):
            return obj.borrow_record.member_id == user.pk
        return False
