from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    pass


class PasswordResetTokenGeneratorCustom(PasswordResetTokenGenerator):
    pass


email_verification_token = EmailVerificationTokenGenerator()
password_reset_token = PasswordResetTokenGeneratorCustom()
