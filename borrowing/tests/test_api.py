from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from books.models import Author, Book, Publisher
from borrowing.models import BorrowRecord, Fine
from users.models import MemberProfile, User


def make_user(username, role, password="Pass12345!"):
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
            {"username": username, "password": "Pass12345!"},
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
        self.assertIsNotNone(response.data.get("fine"))
        self.assertEqual(
            Decimal(response.data["fine"]["amount"]),
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

    def test_borrow_limit_enforced(self):
        books = []
        for i in range(4):
            books.append(
                Book.objects.create(
                    title=f"Limit Book {i}",
                    isbn=f"333333333333{i}",
                    total_copies=1,
                    available_copies=1,
                )
            )
        self._login("mem_br")
        for book in books[:3]:
            response = self.client.post(
                "/api/borrows/borrow/",
                {"book_id": book.id},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        blocked = self.client.post(
            "/api/borrows/borrow/",
            {"book_id": books[3].id},
            format="json",
        )
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("limit", str(blocked.data).lower())

    def test_staff_borrow_requires_member_id(self):
        self._login("lib_br")
        response = self.client.post(
            "/api/borrows/borrow/",
            {"book_id": self.book.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("member_id", response.data)

    def test_member_cannot_borrow_for_another(self):
        self._login("mem_br")
        response = self.client.post(
            "/api/borrows/borrow/",
            {"book_id": self.book.id, "member_id": self.other.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_cannot_pay_fine(self):
        record = BorrowRecord.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() - timedelta(days=1),
            status=BorrowRecord.Status.RETURNED,
            returned_at=timezone.now(),
        )
        fine = Fine.objects.create(
            borrow_record=record,
            amount=Decimal("1.00"),
            reason="Late",
        )
        self._login("mem_br")
        response = self.client.post(f"/api/fines/{fine.id}/pay/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_double_return_rejected(self):
        self._login("mem_br")
        borrow = self.client.post(
            "/api/borrows/borrow/",
            {"book_id": self.book.id},
            format="json",
        )
        record_id = borrow.data["id"]
        first = self.client.post(
            "/api/borrows/return/",
            {"borrow_record_id": record_id},
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        second = self.client.post(
            "/api/borrows/return/",
            {"borrow_record_id": record_id},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pending_fine_blocks_borrow(self):
        prior = BorrowRecord.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() - timedelta(days=1),
            status=BorrowRecord.Status.RETURNED,
            returned_at=timezone.now(),
        )
        Fine.objects.create(
            borrow_record=prior,
            amount=Decimal("2.00"),
            reason="Late",
        )
        other = Book.objects.create(
            title="Blocked",
            isbn="4444444444444",
            total_copies=1,
            available_copies=1,
        )
        self._login("mem_br")
        response = self.client.post(
            "/api/borrows/borrow/",
            {"book_id": other.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fine", str(response.data).lower())

    def test_staff_can_mark_lost(self):
        record = BorrowRecord.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() + timedelta(days=7),
            status=BorrowRecord.Status.BORROWED,
        )
        self.book.available_copies = 1
        self.book.save(update_fields=["available_copies"])
        self._login("lib_br")
        response = self.client.post(f"/api/borrows/{record.id}/mark-lost/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "LOST")
        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 1)

    def test_pay_already_paid_rejected(self):
        record = BorrowRecord.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() - timedelta(days=1),
            status=BorrowRecord.Status.RETURNED,
            returned_at=timezone.now(),
        )
        fine = Fine.objects.create(
            borrow_record=record,
            amount=Decimal("1.00"),
            reason="Late",
            status=Fine.Status.PAID,
            paid_at=timezone.now(),
        )
        self._login("admin_br")
        response = self.client.post(f"/api/fines/{fine.id}/pay/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_promotes_past_due_to_overdue_status(self):
        record = BorrowRecord.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() - timedelta(days=2),
            status=BorrowRecord.Status.BORROWED,
        )
        self._login("mem_br")
        response = self.client.get("/api/borrows/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = response.data["results"][0]
        self.assertEqual(row["id"], record.id)
        # API shows effective OVERDUE without write-on-read
        self.assertEqual(row["status"], "OVERDUE")
        self.assertTrue(row["is_overdue"])

    def test_member_cannot_retrieve_others_borrow(self):
        record = BorrowRecord.objects.create(
            member=self.other,
            book=self.book,
            due_date=timezone.localdate() + timedelta(days=7),
            status=BorrowRecord.Status.BORROWED,
        )
        self._login("mem_br")
        response = self.client.get(f"/api/borrows/{record.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_overdue_filter_includes_synced_overdue(self):
        BorrowRecord.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() - timedelta(days=1),
            status=BorrowRecord.Status.BORROWED,
        )
        on_time = Book.objects.create(
            title="On Time",
            isbn="5555555555555",
            total_copies=1,
            available_copies=0,
        )
        BorrowRecord.objects.create(
            member=self.member,
            book=on_time,
            due_date=timezone.localdate() + timedelta(days=5),
            status=BorrowRecord.Status.BORROWED,
        )
        self._login("mem_br")
        overdue = self.client.get("/api/borrows/?overdue=true")
        self.assertEqual(overdue.status_code, status.HTTP_200_OK)
        self.assertEqual(len(overdue.data["results"]), 1)
        self.assertEqual(overdue.data["results"][0]["status"], "OVERDUE")

        not_overdue = self.client.get("/api/borrows/?overdue=false")
        self.assertEqual(not_overdue.status_code, status.HTTP_200_OK)
        statuses = {row["status"] for row in not_overdue.data["results"]}
        self.assertNotIn("OVERDUE", statuses)

    def test_lost_does_not_consume_borrow_limit(self):
        """LOST frees the limit slot; unique title remains blocked until resolve."""
        books = []
        for i in range(4):
            books.append(
                Book.objects.create(
                    title=f"Limit Lost {i}",
                    isbn=f"666666666666{i}",
                    total_copies=1,
                    available_copies=1,
                )
            )
        # Fill limit with 3 open loans, mark one lost → slot frees
        self._login("mem_br")
        ids = []
        for book in books[:3]:
            response = self.client.post(
                "/api/borrows/borrow/",
                {"book_id": book.id},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            ids.append(response.data["id"])

        self._login("lib_br")
        lost = self.client.post(f"/api/borrows/{ids[0]}/mark-lost/")
        self.assertEqual(lost.status_code, status.HTTP_200_OK)

        self._login("mem_br")
        # 2 open + 1 lost → can borrow a 3rd open loan (limit 3)
        fourth = self.client.post(
            "/api/borrows/borrow/",
            {"book_id": books[3].id},
            format="json",
        )
        self.assertEqual(fourth.status_code, status.HTTP_201_CREATED)

        # Same lost title still blocked
        blocked_same = self.client.post(
            "/api/borrows/borrow/",
            {"book_id": books[0].id},
            format="json",
        )
        self.assertEqual(blocked_same.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resolve_lost_writeoff_and_restore(self):
        record = BorrowRecord.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() + timedelta(days=7),
            status=BorrowRecord.Status.LOST,
        )
        self.book.available_copies = 1
        self.book.save(update_fields=["available_copies"])

        self._login("lib_br")
        writeoff = self.client.post(
            f"/api/borrows/{record.id}/resolve-lost/",
            {"restore_inventory": False},
            format="json",
        )
        self.assertEqual(writeoff.status_code, status.HTTP_200_OK)
        self.assertEqual(writeoff.data["status"], "RETURNED")
        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 1)

        # Can borrow that title again after resolve
        self._login("mem_br")
        again = self.client.post(
            "/api/borrows/borrow/",
            {"book_id": self.book.id},
            format="json",
        )
        self.assertEqual(again.status_code, status.HTTP_201_CREATED)

        # Mark lost again then restore inventory
        self._login("lib_br")
        self.client.post(f"/api/borrows/{again.data['id']}/mark-lost/")
        self.book.refresh_from_db()
        available_before_restore = self.book.available_copies
        restored = self.client.post(
            f"/api/borrows/{again.data['id']}/resolve-lost/",
            {"restore_inventory": True},
            format="json",
        )
        self.assertEqual(restored.status_code, status.HTTP_200_OK)
        self.book.refresh_from_db()
        self.assertEqual(
            self.book.available_copies,
            available_before_restore + 1,
        )

    def test_waived_fine_cannot_be_paid(self):
        record = BorrowRecord.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() - timedelta(days=1),
            status=BorrowRecord.Status.RETURNED,
            returned_at=timezone.now(),
        )
        fine = Fine.objects.create(
            borrow_record=record,
            amount=Decimal("1.00"),
            reason="Late",
            status=Fine.Status.WAIVED,
        )
        self._login("admin_br")
        response = self.client.post(f"/api/fines/{fine.id}/pay/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
