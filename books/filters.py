import django_filters

from .models import Book


class BookFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr="icontains")
    isbn = django_filters.CharFilter(lookup_expr="iexact")
    language = django_filters.CharFilter(lookup_expr="iexact")
    publisher = django_filters.NumberFilter(field_name="publisher_id")
    author = django_filters.NumberFilter(field_name="authors__id")
    category = django_filters.NumberFilter(field_name="categories__id")
    available = django_filters.BooleanFilter(method="filter_available")
    min_copies = django_filters.NumberFilter(
        field_name="available_copies",
        lookup_expr="gte",
    )

    class Meta:
        model = Book
        fields = [
            "title",
            "isbn",
            "language",
            "publisher",
            "author",
            "category",
            "available",
            "min_copies",
        ]

    def filter_available(self, queryset, name, value):
        if value is True:
            return queryset.filter(available_copies__gt=0)
        if value is False:
            return queryset.filter(available_copies=0)
        return queryset
