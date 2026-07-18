from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse


def send_verification_email(user, request):

    uid = user.pk

    token = email_verification_token.make_token(
        user
    )


    verification_link = (
        f"http://127.0.0.1:8000"
        f"/api/auth/verify-email/{uid}/{token}/"
    )


    send_mail(
        subject="Verify your Library Account",

        message=f"""
Hello {user.username},

Click this link to verify your email:

{verification_link}

Thank you.
""",

        from_email=settings.EMAIL_HOST_USER,

        recipient_list=[
            user.email
        ],
    )