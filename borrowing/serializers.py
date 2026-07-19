from rest_framework import serializers

from .models import BorrowRecord, Fine
from .services import (
    borrow_book,
    mark_borrow_lost,
    mark_fine_paid,
    resolve_lost,
    return_book,
)


class FineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fine
        fields = [
            "id",
            "borrow_record",
            "amount",
            "reason",
            "status",
            "paid_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class BorrowRecordSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    member_username = serializers.CharField(
        source="member.username",
        read_only=True,
    )
    status = serializers.CharField(source="display_status", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    fine = FineSerializer(read_only=True)

    class Meta:
        model = BorrowRecord
        fields = [
            "id",
            "member",
            "member_username",
            "book",
            "book_title",
            "borrowed_at",
            "due_date",
            "returned_at",
            "status",
            "notes",
            "is_overdue",
            "fine",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class BorrowCreateSerializer(serializers.Serializer):
    book_id = serializers.IntegerField()
    member_id = serializers.IntegerField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        request = self.context["request"]
        return borrow_book(
            actor=request.user,
            book_id=validated_data["book_id"],
            member_id=validated_data.get("member_id"),
            notes=validated_data.get("notes", ""),
        )


class ReturnBookSerializer(serializers.Serializer):
    """Body optional when returning via /borrows/{id}/return/."""

    borrow_record_id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        if (
            "borrow_record" not in self.context
            and attrs.get("borrow_record_id") is None
        ):
            raise serializers.ValidationError(
                {"borrow_record_id": ["This field is required."]}
            )
        return attrs

    def save(self, **kwargs):
        request = self.context["request"]
        record_id = self.validated_data.get("borrow_record_id")
        if record_id is None:
            record_id = self.context["borrow_record"].pk
        record, fine = return_book(
            actor=request.user,
            borrow_record_id=record_id,
        )
        self.fine = fine
        return record


class MarkLostSerializer(serializers.Serializer):
    def save(self, **kwargs):
        request = self.context["request"]
        record = self.context["borrow_record"]
        return mark_borrow_lost(
            actor=request.user,
            borrow_record_id=record.pk,
        )


class ResolveLostSerializer(serializers.Serializer):
    restore_inventory = serializers.BooleanField(default=False)

    def save(self, **kwargs):
        request = self.context["request"]
        record = self.context["borrow_record"]
        return resolve_lost(
            actor=request.user,
            borrow_record_id=record.pk,
            restore_inventory=self.validated_data.get(
                "restore_inventory", False
            ),
        )


class FinePaySerializer(serializers.Serializer):
    def save(self, **kwargs):
        request = self.context["request"]
        fine = self.context["fine"]
        return mark_fine_paid(actor=request.user, fine_id=fine.pk)
