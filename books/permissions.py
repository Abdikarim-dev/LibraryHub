from rest_framework.permissions import SAFE_METHODS, BasePermission

from users.models import User


class IsAdminOrLibrarianOrReadOnly(BasePermission):
    """
    Authenticated users can read.
    Admin/Librarian can write.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.role in (
            User.Role.ADMIN,
            User.Role.LIBRARIAN,
        )
