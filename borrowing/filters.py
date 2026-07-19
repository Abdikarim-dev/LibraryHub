import django_filters

from .models import BorrowRecord, Fine


class BorrowRecordFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(lookup_expr="iexact")
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

    def filter_overdue(self, queryset, name, value):
        from django.utils import timezone

        today = timezone.localdate()
        if value is True:
            return queryset.filter(
                status=BorrowRecord.Status.BORROWED,
                due_date__lt=today,
            )
        if value is False:
            return queryset.exclude(
                status=BorrowRecord.Status.BORROWED,
                due_date__lt=today,
            )
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
