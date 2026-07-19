import logging
import uuid

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import MemberProfile, User

logger = logging.getLogger(__name__)


def generate_membership_id(user_id: int) -> str:
    return f"MEM-{user_id:05d}-{uuid.uuid4().hex[:6].upper()}"


@receiver(post_save, sender=User)
def create_member_profile(sender, instance, created, **kwargs):
    """Auto-create MemberProfile + membership id for new MEMBER users."""
    if not created:
        return
    if instance.role != User.Role.MEMBER:
        return
    if MemberProfile.objects.filter(user=instance).exists():
        return

    profile = MemberProfile.objects.create(
        user=instance,
        membership_id=generate_membership_id(instance.pk),
    )
    logger.info(
        "member_profile_created user_id=%s membership_id=%s",
        instance.pk,
        profile.membership_id,
    )
