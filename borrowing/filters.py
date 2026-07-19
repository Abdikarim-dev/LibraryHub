import django_filters
from django.utils import timezone

from .models import BorrowRecord, Fine
from .services import overdue_q


class BorrowRecordFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(method="filter_status")
    member = django_filters.NumberFilter(field_name="member_id")
    book = django_filters.NumberFilter(field_name="book_id")
    due_before = django_filters.DateFilter(
        field_name="due_date",
        lookup_expr="lte",
    )
    due_after = django_filters.DateFilter(
        field_name="due_date",
        lookup_expr="gte",
    )
    overdue = django_filters.BooleanFilter(method="filter_overdue")

    class Meta:
        model = BorrowRecord
        fields = [
            "status",
            "member",
            "book",
            "due_before",
            "due_after",
            "overdue",
        ]

    def filter_status(self, queryset, name, value):
        if not value:
            return queryset
        value = value.upper()
        # Treat OVERDUE as effective status (includes past-due BORROWED)
        if value == BorrowRecord.Status.OVERDUE:
            return queryset.filter(overdue_q())
        return queryset.filter(status__iexact=value)

    def filter_overdue(self, queryset, name, value):
        overdue = overdue_q(timezone.localdate())
        if value is True:
            return queryset.filter(overdue)
        if value is False:
            return queryset.exclude(overdue)
        return queryset


class FineFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(lookup_expr="iexact")
    member = django_filters.NumberFilter(
        field_name="borrow_record__member_id"
    )
    min_amount = django_filters.NumberFilter(
        field_name="amount",
        lookup_expr="gte",
    )

    class Meta:
        model = Fine
        fields = ["status", "member", "min_amount"]
