from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .tokens import email_verification_token, password_reset_token
from .utils import send_password_reset_email, send_verification_email


def register_user(*, validated_data, request=None):
    user = User.objects.create_user(**validated_data)
    user.email_verified = False
    user.save(update_fields=["email_verified"])
    send_verification_email(user, request)
    return user


def verify_email(*, uid, token):
    token = (token or "").replace("=", "")
    user = get_object_or_404(User, id=uid)

    if not email_verification_token.check_token(user, token):
        raise ValidationError({"error": "Invalid or expired token"})

    user.email_verified = True
    user.save(update_fields=["email_verified"])
    return user


def change_password(*, user, old_password, new_password):
    if not user.check_password(old_password):
        raise ValidationError({"old_password": ["Old password is incorrect"]})

    user.set_password(new_password)
    user.save()
    return user


def request_password_reset(*, email, request=None):
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist as exc:
        raise ValidationError(
            {"email": ["No account found with this email"]}
        ) from exc

    send_password_reset_email(user, request)
    return user


def reset_password(*, uid, token, new_password):
    token = (token or "").replace("=", "")
    user = get_object_or_404(User, id=uid)

    if not password_reset_token.check_token(user, token):
        raise ValidationError({"error": "Invalid or expired token"})

    user.set_password(new_password)
    user.save()
    return user


def logout(*, refresh_token):
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except Exception as exc:
        raise ValidationError(
            {"refresh": ["Invalid refresh token"]}
        ) from exc


def update_user(*, actor, user, validated_data):
    protected = {"password", "role", "is_superuser", "is_staff", "deleted_at"}
    for field, value in validated_data.items():
        if field in protected:
            continue
        setattr(user, field, value)
    user.save()
    return user


def soft_delete_user(*, actor, user):
    if actor.pk == user.pk:
        raise ValidationError({"detail": "You cannot delete your own account."})

    if user.role == User.Role.ADMIN:
        admin_count = User.objects.filter(role=User.Role.ADMIN).count()
        if admin_count <= 1:
            raise ValidationError(
                {"detail": "Cannot delete the last admin account."}
            )

    user.soft_delete()
    return user


def set_user_role(*, actor, user, role):
    if role not in User.Role.values:
        raise ValidationError({"role": ["Invalid role."]})

    if user.role == User.Role.ADMIN and role != User.Role.ADMIN:
        admin_count = User.objects.filter(role=User.Role.ADMIN).count()
        if admin_count <= 1:
            raise ValidationError(
                {"detail": "Cannot demote the last admin account."}
            )

    user.role = role
    # Keep Django staff flags loosely in sync for admin site convenience
    if role == User.Role.ADMIN:
        user.is_staff = True
    user.save(update_fields=["role", "is_staff"])
    return user


def activate_user(*, actor, user):
    if user.deleted_at is not None:
        raise ValidationError(
            {"detail": "Restore the soft-deleted user before activating."}
        )
    user.activate()
    return user


def deactivate_user(*, actor, user):
    if actor.pk == user.pk:
        raise ValidationError({"detail": "You cannot deactivate yourself."})

    if user.role == User.Role.ADMIN:
        active_admins = User.objects.filter(
            role=User.Role.ADMIN, is_active=True
        ).count()
        if active_admins <= 1:
            raise ValidationError(
                {"detail": "Cannot deactivate the last active admin."}
            )

    user.deactivate()
    return user
