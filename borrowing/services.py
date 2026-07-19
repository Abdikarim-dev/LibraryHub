from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from books.models import Book
from common.exceptions import InventoryIntegrityError
from users.models import User

from .models import BorrowRecord, Fine


def _loan_days():
    return int(getattr(settings, "LIBRARY_LOAN_DAYS", 14))


def _fine_per_day():
    return Decimal(str(getattr(settings, "LIBRARY_FINE_PER_DAY", "1.00")))


def _block_on_pending_fines():
    return bool(
        getattr(settings, "LIBRARY_BLOCK_BORROW_ON_PENDING_FINES", True)
    )


def _active_borrow_count(member):
    return BorrowRecord.objects.filter(
        member=member,
        status__in=BorrowRecord.ACTIVE_STATUSES,
    ).count()


def _borrow_limit(member):
    profile = getattr(member, "member_profile", None)
    if profile is not None:
        return profile.max_borrow_limit
    return 5


def _has_pending_fines(member):
    return Fine.objects.filter(
        borrow_record__member=member,
        status=Fine.Status.PENDING,
    ).exists()


def resolve_borrow_member(*, actor, member_id=None):
    if actor.role == User.Role.MEMBER:
        if member_id and int(member_id) != actor.pk:
            raise PermissionDenied(
                "Members can only borrow books for themselves."
            )
        return actor

    if member_id is None:
        raise ValidationError(
            {"member_id": ["member_id is required for staff borrows."]}
        )

    try:
        member = User.objects.get(pk=member_id, role=User.Role.MEMBER)
    except User.DoesNotExist as exc:
        raise ValidationError(
            {"member_id": ["Member not found."]}
        ) from exc

    return member


def sync_overdue_status(record):
    """Promote BORROWED → OVERDUE when past due (idempotent)."""
    if (
        record.status == BorrowRecord.Status.BORROWED
        and record.due_date < timezone.localdate()
    ):
        record.status = BorrowRecord.Status.OVERDUE
        record.save(update_fields=["status", "updated_at"])
    return record


@transaction.atomic
def borrow_book(*, actor, book_id, member_id=None, notes=""):
    member = resolve_borrow_member(actor=actor, member_id=member_id)
    member = User.objects.select_for_update().get(pk=member.pk)

    if not member.is_active or not member.email_verified:
        raise ValidationError(
            {"detail": "Member must be active and email-verified."}
        )

    if _block_on_pending_fines() and _has_pending_fines(member):
        raise ValidationError(
            {"detail": "Cannot borrow while fines are pending."}
        )

    limit = _borrow_limit(member)
    if _active_borrow_count(member) >= limit:
        raise ValidationError(
            {"detail": f"Borrow limit reached ({limit} books)."}
        )

    try:
        book = Book.objects.select_for_update().get(pk=book_id)
    except Book.DoesNotExist as exc:
        raise ValidationError({"book_id": ["Book not found."]}) from exc

    if book.available_copies < 1:
        raise ValidationError({"detail": "Book is not available."})

    if BorrowRecord.objects.filter(
        member=member,
        book=book,
        status__in=BorrowRecord.ACTIVE_STATUSES,
    ).exists():
        raise ValidationError(
            {"detail": "Member already has an active borrow for this book."}
        )

    due_date = timezone.localdate() + timedelta(days=_loan_days())
    try:
        record = BorrowRecord.objects.create(
            member=member,
            book=book,
            due_date=due_date,
            status=BorrowRecord.Status.BORROWED,
            notes=notes or "",
        )
    except IntegrityError as exc:
        raise ValidationError(
            {"detail": "Member already has an active borrow for this book."}
        ) from exc

    book.available_copies -= 1
    book.save(update_fields=["available_copies"])
    return record


def calculate_fine_amount(*, due_date, returned_on=None):
    returned_on = returned_on or timezone.localdate()
    days_late = (returned_on - due_date).days
    if days_late <= 0:
        return Decimal("0.00"), 0
    amount = (_fine_per_day() * days_late).quantize(Decimal("0.01"))
    return amount, days_late


@transaction.atomic
def return_book(*, actor, borrow_record_id):
    try:
        record = (
            BorrowRecord.objects.select_for_update()
            .select_related("book", "member")
            .get(pk=borrow_record_id)
        )
    except BorrowRecord.DoesNotExist as exc:
        raise ValidationError(
            {"borrow_record_id": ["Borrow record not found."]}
        ) from exc

    if actor.role == User.Role.MEMBER and record.member_id != actor.pk:
        raise PermissionDenied("You can only return your own borrows.")

    if record.status == BorrowRecord.Status.RETURNED:
        raise ValidationError({"detail": "Book already returned."})

    if record.status == BorrowRecord.Status.LOST:
        raise ValidationError(
            {"detail": "Lost books cannot be returned; resolve via staff."}
        )

    sync_overdue_status(record)

    book = Book.objects.select_for_update().get(pk=record.book_id)
    now = timezone.now()
    today = timezone.localdate()

    record.returned_at = now
    record.status = BorrowRecord.Status.RETURNED
    record.save(update_fields=["returned_at", "status", "updated_at"])

    book.available_copies += 1
    if book.available_copies > book.total_copies:
        raise InventoryIntegrityError(
            "Inventory inconsistency detected: available_copies "
            "would exceed total_copies."
        )
    book.save(update_fields=["available_copies"])

    amount, days_late = calculate_fine_amount(
        due_date=record.due_date,
        returned_on=today,
    )
    fine = None
    if amount > 0:
        fine, _ = Fine.objects.get_or_create(
            borrow_record=record,
            defaults={
                "amount": amount,
                "reason": f"Late return ({days_late} day(s))",
                "status": Fine.Status.PENDING,
            },
        )

    return record, fine


@transaction.atomic
def mark_borrow_lost(*, actor, borrow_record_id):
    if actor.role not in (User.Role.ADMIN, User.Role.LIBRARIAN):
        raise PermissionDenied("Only staff can mark borrows as lost.")

    try:
        record = (
            BorrowRecord.objects.select_for_update()
            .select_related("book")
            .get(pk=borrow_record_id)
        )
    except BorrowRecord.DoesNotExist as exc:
        raise ValidationError(
            {"borrow_record_id": ["Borrow record not found."]}
        ) from exc

    if record.status == BorrowRecord.Status.RETURNED:
        raise ValidationError({"detail": "Cannot mark a returned book as lost."})
    if record.status == BorrowRecord.Status.LOST:
        raise ValidationError({"detail": "Borrow is already marked lost."})

    # Copy already removed from availability at borrow time; do not restore.
    record.status = BorrowRecord.Status.LOST
    record.save(update_fields=["status", "updated_at"])
    return record


@transaction.atomic
def mark_fine_paid(*, actor, fine_id):
    if actor.role not in (User.Role.ADMIN, User.Role.LIBRARIAN):
        raise PermissionDenied("Only staff can mark fines as paid.")

    try:
        fine = Fine.objects.select_for_update().get(pk=fine_id)
    except Fine.DoesNotExist as exc:
        raise ValidationError({"fine_id": ["Fine not found."]}) from exc

    if fine.status == Fine.Status.PAID:
        raise ValidationError({"detail": "Fine is already paid."})

    fine.mark_paid()
    return fine
