from django.db import transaction
from rest_framework.exceptions import ValidationError

from books.models import Book
from borrowing.models import BorrowRecord


@transaction.atomic
def create_book(*, validated_data):
    authors = validated_data.pop("authors", [])
    categories = validated_data.pop("categories", [])

    total = validated_data.get("total_copies", 1)
    validated_data["available_copies"] = total

    book = Book.objects.create(**validated_data)
    if authors:
        book.authors.set(authors)
    if categories:
        book.categories.set(categories)
    return book


@transaction.atomic
def update_book(*, book, validated_data):
    book = Book.objects.select_for_update().get(pk=book.pk)
    authors = validated_data.pop("authors", None)
    categories = validated_data.pop("categories", None)
    # Discard any client-supplied availability; recompute from loans when needed
    validated_data.pop("available_copies", None)

    if "total_copies" in validated_data:
        new_total = validated_data["total_copies"]
        active_loans = book.borrow_records.filter(
            status__in=BorrowRecord.ACTIVE_STATUSES
        ).count()
        if new_total < active_loans:
            raise ValidationError(
                {
                    "total_copies": [
                        f"Cannot set total_copies below active loans ({active_loans})."
                    ]
                }
            )
        validated_data["available_copies"] = max(new_total - active_loans, 0)

    for attr, value in validated_data.items():
        setattr(book, attr, value)
    book.save()

    if authors is not None:
        book.authors.set(authors)
    if categories is not None:
        book.categories.set(categories)
    return book
