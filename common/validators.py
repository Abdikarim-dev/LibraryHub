from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError


def validate_user_password(password, user=None):
    """Serializer-field helper: raises a list of messages."""
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc


def assert_valid_password(password, user=None, *, field="password"):
    """Service-layer helper: raises a field-keyed DRF ValidationError."""
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise DRFValidationError({field: list(exc.messages)}) from exc
