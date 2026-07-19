from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from books.models import Author, Book, Category, Publisher
from borrowing.models import BorrowRecord, Fine
from users.models import MemberProfile, User


class Phase3ModelTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(
            username="borrower",
            email="borrower@example.com",
            password="pass12345",
            role=User.Role.MEMBER,
            email_verified=True,
        )
        self.profile = MemberProfile.objects.create(
            user=self.member,
            membership_id="MEM-001",
        )
        self.author = Author.objects.create(
            first_name="Jane",
            last_name="Austen",
        )
        self.publisher = Publisher.objects.create(name="Penguin")
        self.category = Category.objects.create(name="Fiction")
        self.book = Book.objects.create(
            title="Pride and Prejudice",
            isbn="9780141439518",
            publisher=self.publisher,
            total_copies=3,
            available_copies=3,
        )
        self.book.authors.add(self.author)
        self.book.categories.add(self.category)

    def test_relationships(self):
        self.assertEqual(self.member.member_profile.membership_id, "MEM-001")
        self.assertEqual(self.book.publisher.name, "Penguin")
        self.assertIn(self.author, self.book.authors.all())
        self.assertIn(self.category, self.book.categories.all())
        self.assertTrue(self.book.is_available)

    def test_category_slug_auto(self):
        self.assertEqual(self.category.slug, "fiction")

    def test_borrow_and_fine(self):
        record = BorrowRecord.objects.create(
            member=self.member,
            book=self.book,
            due_date=timezone.localdate() + timedelta(days=14),
        )
        fine = Fine.objects.create(
            borrow_record=record,
            amount=Decimal("5.00"),
            reason="Late return",
        )
        self.assertEqual(record.fine.amount, Decimal("5.00"))
        fine.mark_paid()
        fine.refresh_from_db()
        self.assertEqual(fine.status, Fine.Status.PAID)
        self.assertIsNotNone(fine.paid_at)
