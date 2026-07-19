import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_member_profile(sender, instance, created, **kwargs):
    """Auto-create MemberProfile for new MEMBER users via shared service."""
    if not created:
        return
    if instance.role != User.Role.MEMBER:
        return

    # Local import avoids circular import at app load
    from .services import ensure_member_profile

    profile = ensure_member_profile(instance)
    logger.info(
        "member_profile_created user_id=%s membership_id=%s",
        instance.pk,
        profile.membership_id,
    )
