from rest_framework.permissions import BasePermission, SAFE_METHODS

from users.models import User


class IsAuthenticatedMemberOrStaff(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
        )


class IsStaffOrReadOwnBorrow(BasePermission):
    """List/retrieve: member sees own; staff sees all. Mutations: authenticated."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role in (User.Role.ADMIN, User.Role.LIBRARIAN):
            return True
        # BorrowRecord
        if hasattr(obj, "member_id"):
            return obj.member_id == user.pk
        # Fine
        if hasattr(obj, "borrow_record"):
            return obj.borrow_record.member_id == user.pk
        return False


class IsAdminOrLibrarian(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role
            in (User.Role.ADMIN, User.Role.LIBRARIAN)
        )
