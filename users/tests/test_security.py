from django.core import mail
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.tests.helpers import make_user
from users.tokens import email_verification_token, password_reset_token


class TokenIsolationTests(APITestCase):
    def test_verify_token_rejected_on_password_reset(self):
        user = make_user(username="tokensep", password="Secret123!")
        verify_token = email_verification_token.make_token(user)
        response = self.client.post(
            f"/api/auth/reset-password/{user.pk}/{verify_token}/",
            {"password": "BrandNew99!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_token_rejected_on_email_verify(self):
        user = make_user(
            username="tokensep2",
            password="Secret123!",
            email_verified=False,
        )
        reset_token = password_reset_token.make_token(user)
        response = self.client.get(
            f"/api/auth/verify-email/{user.pk}/{reset_token}/"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        user.refresh_from_db()
        self.assertFalse(user.email_verified)


class SecurityHardeningTests(APITestCase):
    def test_forgot_password_does_not_enumerate_emails(self):
        make_user(
            username="known",
            email="known@example.com",
            password="Secret123!",
        )
        known = self.client.post(
            "/api/auth/forgot-password/",
            {"email": "known@example.com"},
            format="json",
        )
        unknown = self.client.post(
            "/api/auth/forgot-password/",
            {"email": "missing@example.com"},
            format="json",
        )
        self.assertEqual(known.status_code, status.HTTP_200_OK)
        self.assertEqual(unknown.status_code, status.HTTP_200_OK)
        self.assertEqual(known.data, unknown.data)

    def test_email_change_clears_verification_and_sends_mail(self):
        user = make_user(
            username="changer",
            email="old@example.com",
            password="Secret123!",
        )
        login = self.client.post(
            "/api/auth/login/",
            {"username": "changer", "password": "Secret123!"},
            format="json",
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}"
        )
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                "/api/users/profile/",
                {"email": "new@example.com"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.email, "new@example.com")
        self.assertFalse(user.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("testserver", mail.outbox[0].body)

    def test_weak_password_rejected_on_register(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "weakuser",
                "email": "weak@example.com",
                "password": "123",
                "first_name": "W",
                "last_name": "U",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_change_blacklists_refresh(self):
        user = make_user(username="pwchange", password="Secret123!")
        refresh = str(RefreshToken.for_user(user))
        login = self.client.post(
            "/api/auth/login/",
            {"username": "pwchange", "password": "Secret123!"},
            format="json",
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}"
        )
        response = self.client.post(
            "/api/users/change-password/",
            {
                "old_password": "Secret123!",
                "new_password": "NewerPass1!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        blocked = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": refresh},
            format="json",
        )
        self.assertEqual(blocked.status_code, status.HTTP_401_UNAUTHORIZED)
        blocked_login_refresh = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": login.data["refresh"]},
            format="json",
        )
        self.assertEqual(
            blocked_login_refresh.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
