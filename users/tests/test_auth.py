from django.core import mail
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User
from users.tests.helpers import make_user
from users.tokens import email_verification_token, password_reset_token


class AuthFlowTests(APITestCase):
    def test_register_sends_verification_email(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "newmember",
                "email": "newmember@example.com",
                "password": "secret123",
                "first_name": "New",
                "last_name": "Member",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="newmember")
        self.assertFalse(user.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Verify", mail.outbox[0].subject)

    def test_login_blocked_until_email_verified(self):
        make_user(
            username="unverified",
            password="secret123",
            email_verified=False,
        )
        response = self.client.post(
            "/api/auth/login/",
            {"username": "unverified", "password": "secret123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("verify", str(response.data).lower())

    def test_verify_email_then_login(self):
        user = make_user(
            username="verifyme",
            password="secret123",
            email_verified=False,
        )
        token = email_verification_token.make_token(user)
        verify = self.client.get(
            f"/api/auth/verify-email/{user.pk}/{token}/"
        )
        self.assertEqual(verify.status_code, status.HTTP_200_OK)

        user.refresh_from_db()
        self.assertTrue(user.email_verified)

        login = self.client.post(
            "/api/auth/login/",
            {"username": "verifyme", "password": "secret123"},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertIn("access", login.data)
        self.assertIn("refresh", login.data)

    def test_verify_email_strips_soft_break_equals(self):
        user = make_user(
            username="qpuser",
            password="secret123",
            email_verified=False,
        )
        token = email_verification_token.make_token(user)
        # Simulate quoted-printable soft line break
        corrupted = token[:20] + "=" + token[20:]
        response = self.client.get(
            f"/api/auth/verify-email/{user.pk}/{corrupted}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

    def test_token_refresh_and_logout_blacklist(self):
        user = make_user(username="tokener", password="secret123")
        login = self.client.post(
            "/api/auth/login/",
            {"username": "tokener", "password": "secret123"},
            format="json",
        )
        access = login.data["access"]
        refresh = login.data["refresh"]

        refreshed = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": refresh},
            format="json",
        )
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        # Rotation enabled → old refresh should be blacklisted
        old_refresh_reuse = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": refresh},
            format="json",
        )
        self.assertEqual(
            old_refresh_reuse.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        # Login again for a clean pair, then logout
        login2 = self.client.post(
            "/api/auth/login/",
            {"username": "tokener", "password": "secret123"},
            format="json",
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login2.data['access']}"
        )
        logout = self.client.post(
            "/api/auth/logout/",
            {"refresh": login2.data["refresh"]},
            format="json",
        )
        self.assertEqual(logout.status_code, status.HTTP_205_RESET_CONTENT)

        blocked = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": login2.data["refresh"]},
            format="json",
        )
        self.assertEqual(blocked.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_forgot_and_reset_password(self):
        user = make_user(username="resetter", password="oldpass")
        forgot = self.client.post(
            "/api/auth/forgot-password/",
            {"email": user.email},
            format="json",
        )
        self.assertEqual(forgot.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

        token = password_reset_token.make_token(user)
        reset = self.client.post(
            f"/api/auth/reset-password/{user.pk}/{token}/",
            {"password": "newpass99"},
            format="json",
        )
        self.assertEqual(reset.status_code, status.HTTP_200_OK)

        login_old = self.client.post(
            "/api/auth/login/",
            {"username": "resetter", "password": "oldpass"},
            format="json",
        )
        self.assertEqual(login_old.status_code, status.HTTP_401_UNAUTHORIZED)

        login_new = self.client.post(
            "/api/auth/login/",
            {"username": "resetter", "password": "newpass99"},
            format="json",
        )
        self.assertEqual(login_new.status_code, status.HTTP_200_OK)

    def test_expired_jwt_ignored_on_public_reset_endpoint(self):
        user = make_user(username="publicreset", password="oldpass")
        token = password_reset_token.make_token(user)
        # Expired/junk access token must not block public endpoint
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not.a.valid.jwt")
        response = self.client.post(
            f"/api/auth/reset-password/{user.pk}/{token}/",
            {"password": "brandnew1"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
