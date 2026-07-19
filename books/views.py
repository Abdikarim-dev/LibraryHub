from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from common.pagination import StandardResultsSetPagination
from .filters import BookFilter
from .models import Author, Book, Category, Publisher
from .permissions import IsAdminOrLibrarianOrReadOnly
from .serializers import (
    AuthorSerializer,
    BookListSerializer,
    BookSerializer,
    CategorySerializer,
    PublisherSerializer,
)


class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [IsAdminOrLibrarianOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["first_name", "last_name", "nationality"]
    ordering_fields = ["last_name", "first_name", "created_at"]
    ordering = ["last_name", "first_name"]


class PublisherViewSet(viewsets.ModelViewSet):
    queryset = Publisher.objects.all()
    serializer_class = PublisherSerializer
    permission_classes = [IsAdminOrLibrarianOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name", "email"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.select_related("parent").all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrLibrarianOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name", "slug", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
    lookup_field = "slug"


class BookViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrLibrarianOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = BookFilter
    search_fields = [
        "title",
        "isbn",
        "description",
        "authors__first_name",
        "authors__last_name",
        "publisher__name",
    ]
    ordering_fields = [
        "title",
        "published_date",
        "available_copies",
        "created_at",
    ]
    ordering = ["title"]

    def get_queryset(self):
        return (
            Book.objects.select_related("publisher")
            .prefetch_related("authors", "categories")
            .distinct()
        )

    def get_serializer_class(self):
        if self.action == "list":
            return BookListSerializer
        return BookSerializer
