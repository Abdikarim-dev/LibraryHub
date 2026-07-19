from rest_framework import status
from rest_framework.test import APITestCase

from users.models import MemberProfile, User


class MembershipSignalTests(APITestCase):
    def test_member_profile_created_on_register(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "signaluser",
                "email": "signaluser@example.com",
                "password": "secret123",
                "first_name": "Sig",
                "last_name": "Nal",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="signaluser")
        self.assertTrue(
            MemberProfile.objects.filter(user=user).exists()
        )
        self.assertTrue(user.member_profile.membership_id.startswith("MEM-"))
