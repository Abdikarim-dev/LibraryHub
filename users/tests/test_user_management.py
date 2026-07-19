from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User
from users.tests.helpers import make_user


class UserManagementTests(APITestCase):
    def setUp(self):
        self.admin = make_user(
            username="admin1",
            password="Pass12345!",
            role=User.Role.ADMIN,
        )
        self.librarian = make_user(
            username="lib1",
            password="Pass12345!",
            role=User.Role.LIBRARIAN,
        )
        self.member = make_user(
            username="mem1",
            password="Pass12345!",
            role=User.Role.MEMBER,
        )
        self.other = make_user(
            username="mem2",
            password="Pass12345!",
            role=User.Role.MEMBER,
        )

    def _login(self, username, password="Pass12345!"):
        response = self.client.post(
            "/api/auth/login/",
            {"username": username, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )
        return response.data

    def test_member_cannot_list_users(self):
        self._login("mem1")
        response = self.client.get("/api/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_librarian_can_list_and_retrieve(self):
        self._login("lib1")
        listing = self.client.get("/api/users/")
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(listing.data["results"]), 1)

        detail = self.client.get(f"/api/users/{self.member.pk}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data["username"], "mem1")

    def test_librarian_cannot_change_role(self):
        self._login("lib1")
        response = self.client.patch(
            f"/api/users/{self.member.pk}/role/",
            {"role": "LIBRARIAN"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_user(self):
        self._login("admin1")
        response = self.client.patch(
            f"/api/users/{self.member.pk}/",
            {"first_name": "Patched"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Patched")

    def test_admin_can_set_role(self):
        self._login("admin1")
        response = self.client.patch(
            f"/api/users/{self.member.pk}/role/",
            {"role": "LIBRARIAN"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.member.refresh_from_db()
        self.assertEqual(self.member.role, User.Role.LIBRARIAN)

    def test_admin_can_deactivate_and_activate(self):
        self._login("admin1")
        deactivated = self.client.patch(
            f"/api/users/{self.other.pk}/deactivate/"
        )
        self.assertEqual(deactivated.status_code, status.HTTP_200_OK)
        self.other.refresh_from_db()
        self.assertFalse(self.other.is_active)

        activated = self.client.patch(
            f"/api/users/{self.other.pk}/activate/"
        )
        self.assertEqual(activated.status_code, status.HTTP_200_OK)
        self.other.refresh_from_db()
        self.assertTrue(self.other.is_active)

    def test_admin_soft_delete_hides_user(self):
        self._login("admin1")
        deleted = self.client.delete(f"/api/users/{self.other.pk}/")
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(User.objects.filter(pk=self.other.pk).exists())
        self.assertTrue(
            User.all_objects.filter(pk=self.other.pk).exists()
        )

        listing = self.client.get("/api/users/")
        ids = [row["id"] for row in listing.data["results"]]
        self.assertNotIn(self.other.pk, ids)

    def test_admin_cannot_delete_self(self):
        self._login("admin1")
        response = self.client.delete(f"/api/users/{self.admin.pk}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_demote_last_admin(self):
        self._login("admin1")
        response = self.client.patch(
            f"/api/users/{self.admin.pk}/role/",
            {"role": "MEMBER"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, User.Role.ADMIN)

    def test_cannot_deactivate_last_admin(self):
        self._login("admin1")
        response = self.client.patch(
            f"/api/users/{self.admin.pk}/deactivate/"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_librarian_list_hides_sensitive_fields(self):
        self._login("lib1")
        detail = self.client.get(f"/api/users/{self.member.pk}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertNotIn("phone_number", detail.data)
        self.assertNotIn("deleted_at", detail.data)

    def test_librarian_cannot_patch_user(self):
        self._login("lib1")
        response = self.client.patch(
            f"/api/users/{self.member.pk}/",
            {"first_name": "Nope"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_deactivate_blacklists_refresh(self):
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = str(RefreshToken.for_user(self.other))
        self._login("admin1")
        response = self.client.patch(
            f"/api/users/{self.other.pk}/deactivate/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        blocked = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": refresh},
            format="json",
        )
        self.assertEqual(blocked.status_code, status.HTTP_401_UNAUTHORIZED)
