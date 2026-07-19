import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import BorrowRecord, Fine

logger = logging.getLogger(__name__)


@receiver(post_save, sender=BorrowRecord)
def log_borrow_record(sender, instance, created, **kwargs):
    if created:
        logger.info(
            "borrow_created id=%s member_id=%s book_id=%s due=%s",
            instance.pk,
            instance.member_id,
            instance.book_id,
            instance.due_date,
        )
        return

    logger.info(
        "borrow_updated id=%s status=%s returned_at=%s",
        instance.pk,
        instance.status,
        instance.returned_at,
    )


@receiver(post_save, sender=Fine)
def notify_fine_created(sender, instance, created, **kwargs):
    """Placeholder notification hook (email/push can plug in later)."""
    if not created:
        return
    logger.warning(
        "fine_notification borrow_id=%s member_id=%s amount=%s reason=%s",
        instance.borrow_record_id,
        instance.borrow_record.member_id,
        instance.amount,
        instance.reason,
    )
