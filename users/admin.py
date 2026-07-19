from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import MemberProfile, User


class MemberProfileInline(admin.StackedInline):
    model = MemberProfile
    can_delete = False
    extra = 0


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = [MemberProfileInline]
    list_display = (
        "username",
        "email",
        "role",
        "email_verified",
        "is_active",
        "deleted_at",
        "date_joined",
    )
    list_filter = (
        "role",
        "email_verified",
        "is_active",
        "is_staff",
    )
    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
    )
    fieldsets = UserAdmin.fieldsets + (
        (
            "Additional Information",
            {
                "fields": (
                    "role",
                    "email_verified",
                    "phone_number",
                    "profile_image",
                    "deleted_at",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Additional Information",
            {
                "fields": (
                    "role",
                    "email",
                )
            },
        ),
    )

    def get_queryset(self, request):
        return User.all_objects.all()


@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = (
        "membership_id",
        "user",
        "max_borrow_limit",
        "date_of_birth",
        "created_at",
    )
    search_fields = (
        "membership_id",
        "user__username",
        "user__email",
    )
    autocomplete_fields = ("user",)
