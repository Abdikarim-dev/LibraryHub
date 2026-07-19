from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from common.pagination import StandardResultsSetPagination
from users.models import User

from .filters import BorrowRecordFilter, FineFilter
from .models import BorrowRecord, Fine
from .permissions import IsAdminOrLibrarian, IsStaffOrReadOwnBorrow
from .serializers import (
    BorrowCreateSerializer,
    BorrowRecordSerializer,
    FinePaySerializer,
    FineSerializer,
    ReturnBookSerializer,
)


class BorrowRecordViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsStaffOrReadOwnBorrow]
    serializer_class = BorrowRecordSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = BorrowRecordFilter
    search_fields = [
        "book__title",
        "book__isbn",
        "member__username",
        "member__email",
    ]
    ordering_fields = ["borrowed_at", "due_date", "status", "created_at"]
    ordering = ["-borrowed_at"]

    def get_queryset(self):
        qs = BorrowRecord.objects.select_related(
            "book",
            "member",
        ).prefetch_related("fine")
        user = self.request.user
        if user.role in (User.Role.ADMIN, User.Role.LIBRARIAN):
            return qs.all()
        return qs.filter(member=user)

    @action(detail=False, methods=["post"], url_path="borrow")
    def borrow(self, request):
        serializer = BorrowCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        record = serializer.save()
        return Response(
            BorrowRecordSerializer(record, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="return")
    def return_book_action(self, request):
        serializer = ReturnBookSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        record = serializer.save()
        payload = BorrowRecordSerializer(
            record,
            context={"request": request},
        ).data
        if getattr(serializer, "fine", None) is not None:
            payload["fine_created"] = FineSerializer(serializer.fine).data
        return Response(payload, status=status.HTTP_200_OK)


class FineViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsStaffOrReadOwnBorrow]
    serializer_class = FineSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = FineFilter
    search_fields = [
        "reason",
        "borrow_record__book__title",
        "borrow_record__member__username",
    ]
    ordering_fields = ["amount", "status", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Fine.objects.select_related(
            "borrow_record",
            "borrow_record__member",
            "borrow_record__book",
        )
        user = self.request.user
        if user.role in (User.Role.ADMIN, User.Role.LIBRARIAN):
            return qs.all()
        return qs.filter(borrow_record__member=user)

    @action(
        detail=True,
        methods=["post"],
        url_path="pay",
        permission_classes=[IsAdminOrLibrarian],
    )
    def pay(self, request, pk=None):
        fine = self.get_object()
        serializer = FinePaySerializer(
            data=request.data,
            context={"request": request, "fine": fine},
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(FineSerializer(updated).data)
