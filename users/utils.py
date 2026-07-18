import logging

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from .tokens import email_verification_token

logger = logging.getLogger(__name__)


def send_verification_email(user, request):
    token = email_verification_token.make_token(user)
    path = reverse("verify-email", args=[user.pk, token])
    verification_link = request.build_absolute_uri(path)

    subject = "Verify your Library Account"
    message = (
        f"Hello {user.username},\n\n"
        f"Click this link to verify your email:\n\n"
        f"{verification_link}\n\n"
        f"Thank you."
    )
    from_email = (
        getattr(settings, "DEFAULT_FROM_EMAIL", None)
        or getattr(settings, "EMAIL_HOST_USER", None)
        or None
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            "Failed to send verification email to user_id=%s",
            user.pk,
        )
        return False

    return True
