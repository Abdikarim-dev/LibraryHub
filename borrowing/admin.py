from django.contrib import admin

from .models import BorrowRecord, Fine


class FineInline(admin.StackedInline):
    model = Fine
    extra = 0


@admin.register(BorrowRecord)
class BorrowRecordAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "member",
        "book",
        "status",
        "borrowed_at",
        "due_date",
        "returned_at",
    )
    list_filter = ("status", "due_date")
    search_fields = (
        "member__username",
        "member__email",
        "book__title",
        "book__isbn",
    )
    inlines = [FineInline]
    autocomplete_fields = ("member", "book")


@admin.register(Fine)
class FineAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "borrow_record",
        "amount",
        "status",
        "paid_at",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = (
        "borrow_record__member__username",
        "borrow_record__book__title",
    )
