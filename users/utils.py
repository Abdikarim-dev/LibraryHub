import logging

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from .tokens import email_verification_token, password_reset_token

logger = logging.getLogger(__name__)


def _from_email():
    return (
        getattr(settings, "DEFAULT_FROM_EMAIL", None)
        or getattr(settings, "EMAIL_HOST_USER", None)
        or None
    )


def _absolute_url(request, path):
    if request is not None:
        return request.build_absolute_uri(path)
    base = getattr(settings, "PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip(
        "/"
    )
    return f"{base}{path}"


def send_verification_email(user, request):
    token = email_verification_token.make_token(user)
    path = reverse("verify-email", args=[user.pk, token])
    verification_link = _absolute_url(request, path)

    subject = "Verify your Library Account"
    message = (
        f"Hello {user.username},\n\n"
        f"Open this link to verify your email:\n"
        f"{verification_link}\n\n"
        f"Thank you."
    )
    html_message = (
        f"<p>Hello {user.username},</p>"
        f"<p>"
        f'<a href="{verification_link}">Click here to verify your email</a>'
        f"</p>"
        f"<p>Thank you.</p>"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=_from_email(),
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            "Failed to send verification email to user_id=%s",
            user.pk,
        )
        return False

    return True


def send_password_reset_email(user, request=None):
    token = password_reset_token.make_token(user)
    path = reverse("reset-password", args=[user.pk, token])
    reset_link = _absolute_url(request, path)

    name = (
        f"{user.first_name} {user.last_name}".strip()
        or user.username
    )
    subject = "Reset Your Library Password"
    message = (
        f"Hello {name},\n\n"
        f"You requested a password reset.\n\n"
        f"Open this link:\n{reset_link}\n\n"
        f"If you did not request this, ignore this email."
    )
    html_message = (
        f"<p>Hello {name},</p>"
        f"<p>You requested a password reset.</p>"
        f"<p>"
        f'<a href="{reset_link}">Click here to reset your password</a>'
        f"</p>"
        f"<p>If you did not request this, ignore this email.</p>"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=_from_email(),
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            "Failed to send password reset email to user_id=%s",
            user.pk,
        )
        return False

    return True
