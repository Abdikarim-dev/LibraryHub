from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(
    PasswordResetTokenGenerator
):
    pass


email_verification_token = (
    EmailVerificationTokenGenerator()
)

from django.contrib.auth.tokens import PasswordResetTokenGenerator


class PasswordResetTokenGeneratorCustom(
    PasswordResetTokenGenerator
):
    pass


password_reset_token = (
    PasswordResetTokenGeneratorCustom()
)