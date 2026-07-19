from rest_framework import status
from rest_framework.test import APITestCase

from users.tests.helpers import make_user


class ProfileTests(APITestCase):
    def setUp(self):
        self.user = make_user(
            username="member1",
            password="secret123",
            first_name="Mem",
            last_name="Ber",
        )
        login = self.client.post(
            "/api/auth/login/",
            {"username": "member1", "password": "secret123"},
            format="json",
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}"
        )

    def test_get_profile(self):
        response = self.client.get("/api/users/profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "member1")
        self.assertIn("profile_image", response.data)

    def test_patch_profile(self):
        response = self.client.patch(
            "/api/users/profile/",
            {"first_name": "Updated", "phone_number": "0612345678"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Updated")
        self.assertEqual(response.data["phone_number"], "0612345678")
        # Role remains read-only for self-profile
        self.assertEqual(response.data["role"], "MEMBER")

    def test_change_password(self):
        response = self.client.post(
            "/api/users/change-password/",
            {
                "old_password": "secret123",
                "new_password": "newerpass1",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.credentials()
        old_login = self.client.post(
            "/api/auth/login/",
            {"username": "member1", "password": "secret123"},
            format="json",
        )
        self.assertEqual(old_login.status_code, status.HTTP_401_UNAUTHORIZED)

        new_login = self.client.post(
            "/api/auth/login/",
            {"username": "member1", "password": "newerpass1"},
            format="json",
        )
        self.assertEqual(new_login.status_code, status.HTTP_200_OK)

    def test_profile_requires_auth(self):
        self.client.credentials()
        response = self.client.get("/api/users/profile/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
