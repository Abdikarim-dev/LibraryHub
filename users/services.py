from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from common.validators import assert_valid_password

from .membership import generate_membership_id
from .models import MemberProfile, User
from .tokens import email_verification_token, password_reset_token
from .utils import send_password_reset_email, send_verification_email

logger = logging.getLogger(__name__)


def blacklist_user_tokens(user: User) -> None:
    """Invalidate all outstanding refresh tokens for a user."""
    for outstanding in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=outstanding)


def _ensure_not_self(actor: User, user: User, action: str = "modify") -> None:
    if actor.pk == user.pk:
        raise ValidationError(
            {"detail": f"You cannot {action} your own account."}
        )


@transaction.atomic
def _ensure_not_last_admin(
    user: User, *, require_active: bool = False
) -> None:
    if user.role != User.Role.ADMIN:
        return
    qs = User.objects.select_for_update().filter(role=User.Role.ADMIN)
    if require_active:
        qs = qs.filter(is_active=True)
    if qs.count() <= 1:
        raise ValidationError(
            {"detail": "Cannot modify the last admin account."}
        )


def ensure_member_profile(user: User) -> MemberProfile:
    profile, _created = MemberProfile.objects.get_or_create(
        user=user,
        defaults={"membership_id": generate_membership_id(user.pk)},
    )
    if not profile.membership_id:
        profile.membership_id = generate_membership_id(user.pk)
        profile.save(update_fields=["membership_id"])
    return profile


@transaction.atomic
def register_user(
    *,
    validated_data: dict[str, Any],
    request: HttpRequest | None = None,
) -> User:
    password = validated_data.get("password")
    assert_valid_password(password)

    user = User.objects.create_user(**validated_data)
    user.email_verified = False
    user.save(update_fields=["email_verified"])
    ensure_member_profile(user)

    transaction.on_commit(
        lambda: _send_verification_or_log(user.pk, request)
    )
    return user


def _send_verification_or_log(
    user_id: int, request: HttpRequest | None
) -> None:
    user = User.objects.filter(pk=user_id).first()
    if not user:
        return
    ok = send_verification_email(user, request)
    if not ok:
        logger.error("verification_email_failed user_id=%s", user_id)


def verify_email(*, uid: int, token: str) -> User:
    token = (token or "").replace("=", "")
    user = get_object_or_404(User, id=uid)

    if not email_verification_token.check_token(user, token):
        raise ValidationError({"detail": "Invalid or expired token"})

    user.email_verified = True
    user.save(update_fields=["email_verified"])
    return user


@transaction.atomic
def change_password(
    *, user: User, old_password: str, new_password: str
) -> User:
    if not user.check_password(old_password):
        raise ValidationError({"old_password": ["Old password is incorrect"]})

    assert_valid_password(new_password, user=user, field="new_password")
    user.set_password(new_password)
    user.save()
    blacklist_user_tokens(user)
    return user


def request_password_reset(
    *, email: str, request: HttpRequest | None = None
) -> User | None:
    """
    Always succeed from the caller's perspective to avoid email enumeration.
    """
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        logger.info("password_reset_unknown_email email=%s", email)
        return None

    send_password_reset_email(user, request)
    return user


@transaction.atomic
def reset_password(*, uid: int, token: str, new_password: str) -> User:
    token = (token or "").replace("=", "")
    user = get_object_or_404(User, id=uid)

    if not password_reset_token.check_token(user, token):
        raise ValidationError({"detail": "Invalid or expired token"})

    assert_valid_password(new_password, user=user)
    user.set_password(new_password)
    user.save()
    blacklist_user_tokens(user)
    return user


def logout(*, refresh_token: str) -> None:
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except TokenError as exc:
        raise ValidationError(
            {"refresh": ["Invalid refresh token"]}
        ) from exc


@transaction.atomic
def update_user(
    *,
    actor: User,
    user: User,
    validated_data: dict[str, Any],
    request: HttpRequest | None = None,
) -> User:
    protected = {"password", "role", "is_superuser", "is_staff", "deleted_at"}
    forbidden = [f for f in validated_data if f in protected]
    if forbidden:
        raise ValidationError(
            {field: ["This field cannot be updated here."] for field in forbidden}
        )

    email_changed = (
        "email" in validated_data
        and validated_data["email"] != user.email
    )

    for field, value in validated_data.items():
        setattr(user, field, value)

    update_fields = list(validated_data.keys())
    if email_changed:
        user.email_verified = False
        update_fields.append("email_verified")

    user.save(update_fields=update_fields or None)

    if email_changed:
        transaction.on_commit(
            lambda: _send_verification_or_log(user.pk, request)
        )
    return user


@transaction.atomic
def soft_delete_user(*, actor: User, user: User) -> User:
    user = User.objects.select_for_update().get(pk=user.pk)
    _ensure_not_self(actor, user, action="delete")
    _ensure_not_last_admin(user)
    user.soft_delete()
    blacklist_user_tokens(user)
    return user


@transaction.atomic
def set_user_role(*, actor: User, user: User, role: str) -> User:
    if role not in User.Role.values:
        raise ValidationError({"role": ["Invalid role."]})

    user = User.objects.select_for_update().get(pk=user.pk)
    if user.role == User.Role.ADMIN and role != User.Role.ADMIN:
        _ensure_not_last_admin(user)

    user.role = role
    user.is_staff = role == User.Role.ADMIN
    user.save(update_fields=["role", "is_staff"])

    if role == User.Role.MEMBER:
        ensure_member_profile(user)
    return user


@transaction.atomic
def activate_user(*, actor: User, user: User) -> User:
    user = User.objects.select_for_update().get(pk=user.pk)
    _ensure_not_self(actor, user, action="activate")
    if user.deleted_at is not None:
        raise ValidationError(
            {"detail": "Restore the soft-deleted user before activating."}
        )
    user.activate()
    return user


@transaction.atomic
def restore_user(*, actor: User, user: User) -> User:
    """Clear soft-delete and reactivate (admin only, via ViewSet)."""
    user = User.all_objects.select_for_update().get(pk=user.pk)
    if user.deleted_at is None:
        raise ValidationError({"detail": "User is not soft-deleted."})
    user.restore()
    return user


@transaction.atomic
def deactivate_user(*, actor: User, user: User) -> User:
    user = User.objects.select_for_update().get(pk=user.pk)
    _ensure_not_self(actor, user, action="deactivate")
    _ensure_not_last_admin(user, require_active=True)
    user.deactivate()
    blacklist_user_tokens(user)
    return user
