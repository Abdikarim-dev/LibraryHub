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

from django.core.mail import send_mail
from django.conf import settings

from .tokens import password_reset_token



def send_password_reset_email(
    user
):

    uid = user.pk


    token = password_reset_token.make_token(
        user
    )


    reset_link = (
        f"http://127.0.0.1:8000"
        f"/api/auth/reset-password/"
        f"{uid}/{token}/"
    )


    send_mail(

        subject="Reset Your Library Password",

        message=f"""
Hello {user.firstname} {user.lastname},

You requested a password reset.

Click this link:

{reset_link}

If you did not request this,
ignore this email.
""",

        from_email=settings.EMAIL_HOST_USER,

        recipient_list=[
            user.email
        ],

    )