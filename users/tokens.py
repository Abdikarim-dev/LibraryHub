from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Purpose-salted so verify tokens cannot be reused for password reset."""

    def _make_hash_value(self, user, timestamp):
        email = getattr(user, user.get_email_field_name(), "") or ""
        return (
            f"email-verify:{user.pk}{user.password}{email}"
            f"{user.email_verified}{timestamp}"
        )


class PasswordResetTokenGeneratorCustom(PasswordResetTokenGenerator):
    """Purpose-salted so reset tokens cannot be reused for email verify."""

    def _make_hash_value(self, user, timestamp):
        login_timestamp = (
            ""
            if user.last_login is None
            else user.last_login.replace(microsecond=0, tzinfo=None)
        )
        email = getattr(user, user.get_email_field_name(), "") or ""
        return (
            f"password-reset:{user.pk}{user.password}"
            f"{login_timestamp}{timestamp}{email}"
        )


email_verification_token = EmailVerificationTokenGenerator()
password_reset_token = PasswordResetTokenGeneratorCustom()
