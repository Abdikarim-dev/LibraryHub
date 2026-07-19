from django.conf import settings
from rest_framework import serializers


def validate_uploaded_image(value):
    """Shared size + Pillow format checks for ImageField uploads."""
    if value is None:
        return value
    max_size = getattr(settings, "MAX_UPLOAD_SIZE_BYTES", 2 * 1024 * 1024)
    if value.size > max_size:
        raise serializers.ValidationError(
            f"Image too large. Max size is {max_size} bytes."
        )
    try:
        from PIL import Image

        image = Image.open(value)
        fmt = (image.format or "").upper()
        image.verify()
    except Exception as exc:
        raise serializers.ValidationError("Invalid image file.") from exc
    finally:
        if hasattr(value, "seek"):
            value.seek(0)

    if fmt not in {"JPEG", "PNG", "WEBP", "GIF"}:
        raise serializers.ValidationError(
            "Unsupported image type. Use JPEG, PNG, WEBP, or GIF."
        )
    return value
