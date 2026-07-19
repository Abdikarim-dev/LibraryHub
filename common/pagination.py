from rest_framework.pagination import (
    CursorPagination,
    LimitOffsetPagination,
    PageNumberPagination,
)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class StandardLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 10
    limit_query_param = "limit"
    offset_query_param = "offset"
    max_limit = 100


class StandardCursorPagination(CursorPagination):
    page_size = 10
    page_size_query_param = "page_size"
    ordering = "-created_at"
