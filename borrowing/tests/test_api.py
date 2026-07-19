from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from books.models import Author, Book, Publisher
from borrowing.models import BorrowRecord, Fine
from users.models import MemberProfile, User


def make_user(username, role, password="pass12345"):
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=password,
        role=role,
        email_verified=True,
        is_active=True,
    )
    if role == User.Role.ADMIN:
        user.is_staff = True
        user.save(update_fields=["is_staff"])
    if role == User.Role.MEMBER:
        profile = getattr(user, "member_profile", None)
        if profile is None:
            MemberProfile.objects.create(
                user=user,
                membership_id=f"MEM-{username}",
                max_borrow_limit=3,
            )
        else:
            profile.max_borrow_limit = 3
            if not profile.membership_id:
                profile.membership_id = f"MEM-{username}"
            profile.save()
    return user


class BorrowReturnAPITests(APITestCase):
    def setUp(self):
        self.admin = make_user("admin_br", User.Role.ADMIN)
        self.librarian = make_user("lib_br", User.Role.LIBRARIAN)
        self.member = make_user("mem_br", User.Role.MEMBER)
        self.other = make_user("mem_other", User.Role.MEMBER)

        self.publisher = Publisher.objects.create(name="Test Pub")
        self.author = Author.objects.create(first_name="A", last_name="B")
        self.book = Book.objects.create(
            title="Borrowable Book",
            isbn="1111111111111",
            publisher=self.publisher,
            total_copies=2,
            available_copies=2,
        )
        self.book.authors.add(self.author)

    def _login(self, username):
        response = self.client.post(
            "/api/auth/login/",
            {"username": username, "password": "pass12345"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )

    def test_member_can_borrow_and_inventory_decrements(self):
        self._login("mem_br")
        response = self.client.post(
            "/api/borrows/borrow/",
            {"book_id": self.book.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "BORROWED")
        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 1)

    def test_prevent_duplicate_active_borrow(self):
        self._login("mem_br")
        first = self.client.post(
            "/api/borrows/borrow/",
            {"book_id": self.book.id},
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        second = self.client.post(
            "/api/borrows/borrow/",
            {"book_id": self.book.id},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unavailable_book_cannot_be_borrowed(self):
        self.book.available_copies = 0
        self.book.save(update_fields=["available_copies"])
        self._login("mem_br")
        response = self.client.post(
            "/api/borrows/borrow/",
            {"book_id": self.book.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_return_increments_inventory(self):
        self._login("mem_br")
        borrow = self.client.post(
            "/api/borrows/borrow/",
            {"book_id": self.book.id},
            format="json",
        )
        record_id = borrow.data["id"]
        returned = self.client.post(
            "/api/borrows/return/",
            {"borrow_record_id": record_id},
            format="json",
        )
        self.assertEqual(returned.status_code, status.HTTP_200_OK)
        self.assertEqual(returned.data["status"], "RETURNED")
        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 2)

    def test_late_return_creates_fine(self):
        record = BorrowRecord.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() - timedelta(days=3),
            status=BorrowRecord.Status.BORROWED,
        )
        self.book.available_copies = 1
        self.book.save(update_fields=["available_copies"])

        self._login("mem_br")
        response = self.client.post(
            "/api/borrows/return/",
            {"borrow_record_id": record.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("fine_created", response.data)
        self.assertEqual(
            Decimal(response.data["fine_created"]["amount"]),
            Decimal("3.00"),
        )
        self.assertTrue(Fine.objects.filter(borrow_record=record).exists())

    def test_member_cannot_return_others_book(self):
        record = BorrowRecord.objects.create(
            member=self.other,
            book=self.book,
            due_date=timezone.localdate() + timedelta(days=7),
            status=BorrowRecord.Status.BORROWED,
        )
        self._login("mem_br")
        response = self.client.post(
            "/api/borrows/return/",
            {"borrow_record_id": record.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_librarian_can_borrow_for_member(self):
        self._login("lib_br")
        response = self.client.post(
            "/api/borrows/borrow/",
            {"book_id": self.book.id, "member_id": self.member.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["member"], self.member.id)

    def test_staff_can_mark_fine_paid(self):
        record = BorrowRecord.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() - timedelta(days=2),
            status=BorrowRecord.Status.RETURNED,
            returned_at=timezone.now(),
        )
        fine = Fine.objects.create(
            borrow_record=record,
            amount=Decimal("2.00"),
            reason="Late",
        )
        self._login("admin_br")
        response = self.client.post(f"/api/fines/{fine.id}/pay/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "PAID")

    def test_member_lists_only_own_borrows(self):
        BorrowRecord.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() + timedelta(days=7),
        )
        other_book = Book.objects.create(
            title="Other",
            isbn="2222222222222",
            total_copies=1,
            available_copies=1,
        )
        BorrowRecord.objects.create(
            member=self.other,
            book=other_book,
            due_date=timezone.localdate() + timedelta(days=7),
        )
        self._login("mem_br")
        response = self.client.get("/api/borrows/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["member"], self.member.id)
