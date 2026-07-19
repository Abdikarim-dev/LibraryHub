from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from common.models import TimeStampedModel


class BorrowRecord(TimeStampedModel):
    class Status(models.TextChoices):
        BORROWED = "BORROWED", "Borrowed"
        RETURNED = "RETURNED", "Returned"
        OVERDUE = "OVERDUE", "Overdue"
        LOST = "LOST", "Lost"

    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="borrow_records",
        limit_choices_to={"role": "MEMBER"},
    )
    book = models.ForeignKey(
        "books.Book",
        on_delete=models.PROTECT,
        related_name="borrow_records",
    )
    borrowed_at = models.DateTimeField(default=timezone.now)
    due_date = models.DateField()
    returned_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.BORROWED,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-borrowed_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["due_date"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["member", "book"],
                condition=models.Q(status="BORROWED"),
                name="unique_active_borrow_per_member_book",
            )
        ]

    def __str__(self):
        return f"{self.member} → {self.book} [{self.status}]"

    @property
    def is_overdue(self):
        if self.status == self.Status.RETURNED:
            return False
        return self.due_date < timezone.localdate()


class Fine(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        WAIVED = "WAIVED", "Waived"

    borrow_record = models.OneToOneField(
        BorrowRecord,
        on_delete=models.CASCADE,
        related_name="fine",
    )
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Fine<{self.amount}> for {self.borrow_record_id}"

    def mark_paid(self):
        self.status = self.Status.PAID
        self.paid_at = timezone.now()
        self.save(update_fields=["status", "paid_at"])
