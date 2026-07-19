from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils import timezone


class ActiveUserManager(UserManager):
    """Default manager: hide soft-deleted users."""

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(deleted_at__isnull=True)
        )


class AllUsersManager(UserManager):
    """Includes soft-deleted users (admin / recovery)."""

    def get_queryset(self):
        return super().get_queryset()


class User(AbstractUser):

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        LIBRARIAN = "LIBRARIAN", "Librarian"
        MEMBER = "MEMBER", "Member"

    email = models.EmailField(
        unique=True,
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )

    email_verified = models.BooleanField(
        default=False,
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
    )

    # No HTTP URL default — ImageField stores files, not remote URLs
    profile_image = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True,
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    objects = ActiveUserManager()
    all_objects = AllUsersManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.username

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save(update_fields=["deleted_at", "is_active"])

    def restore(self):
        self.deleted_at = None
        self.is_active = True
        self.save(update_fields=["deleted_at", "is_active"])

    def activate(self):
        self.is_active = True
        self.save(update_fields=["is_active"])

    def deactivate(self):
        self.is_active = False
        self.save(update_fields=["is_active"])


class MemberProfile(models.Model):
    """
    Extended library-member profile (OneToOne → User).
    membership_id can be auto-generated later via signals (Phase 12).
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="member_profile",
    )
    membership_id = models.CharField(
        max_length=32,
        unique=True,
        blank=True,
        null=True,
    )
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    max_borrow_limit = models.PositiveSmallIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"MemberProfile<{self.user.username}>"
