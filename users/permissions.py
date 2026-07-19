from rest_framework.permissions import BasePermission

from .models import User


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
        )


class IsLibrarian(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.LIBRARIAN
        )


class IsAdminOrLibrarian(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role
            in (User.Role.ADMIN, User.Role.LIBRARIAN)
        )


class IsMember(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.MEMBER
        )
