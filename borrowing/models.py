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

    # Still out with the member — count toward max_borrow_limit
    OPEN_LOAN_STATUSES = (Status.BORROWED, Status.OVERDUE)

    # Occupy a physical copy (and unique member+book slot) until closed
    # LOST: copy write-off until staff resolve-lost; does NOT count toward limit
    ACTIVE_STATUSES = (Status.BORROWED, Status.OVERDUE, Status.LOST)

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
        db_index=True,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-borrowed_at"]
        indexes = [
            models.Index(fields=["status", "due_date"]),
            models.Index(fields=["member", "status"]),
            models.Index(fields=["book", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["member", "book"],
                condition=models.Q(
                    status__in=["BORROWED", "OVERDUE", "LOST"]
                ),
                name="unique_active_borrow_per_member_book",
            )
        ]

    def __str__(self):
        return f"{self.member} → {self.book} [{self.status}]"

    @property
    def display_status(self):
        """Effective status without mutating the DB (past-due BORROWED → OVERDUE)."""
        if (
            self.status == self.Status.BORROWED
            and self.due_date < timezone.localdate()
        ):
            return self.Status.OVERDUE
        return self.status

    @property
    def is_overdue(self):
        if self.status in (self.Status.RETURNED, self.Status.LOST):
            return False
        if self.status == self.Status.OVERDUE:
            return True
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
        db_index=True,
    )
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name="fine_amount_non_negative",
            ),
        ]

    def __str__(self):
        return f"Fine<{self.amount}> for {self.borrow_record_id}"

    def mark_paid(self):
        self.status = self.Status.PAID
        self.paid_at = timezone.now()
        self.save(update_fields=["status", "paid_at"])
