from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from common.pagination import StandardResultsSetPagination
from users.models import User
from users.permissions import IsAdminOrLibrarian

from .filters import BorrowRecordFilter, FineFilter
from .models import BorrowRecord, Fine
from .permissions import IsStaffOrReadOwnBorrow
from .serializers import (
    BorrowCreateSerializer,
    BorrowRecordSerializer,
    FinePaySerializer,
    FineSerializer,
    MarkLostSerializer,
    ResolveLostSerializer,
    ReturnBookSerializer,
)


class BorrowRecordViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET  /api/borrows/              list
    POST /api/borrows/              borrow (create)
    GET  /api/borrows/{id}/         retrieve
    POST /api/borrows/{id}/return/  return
    POST /api/borrows/{id}/mark-lost/
    POST /api/borrows/{id}/resolve-lost/

    Legacy aliases (still accepted):
    POST /api/borrows/borrow/
    POST /api/borrows/return/  (body: borrow_record_id)
    """

    permission_classes = [IsStaffOrReadOwnBorrow]
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

    def get_serializer_class(self):
        if self.action in ("create", "borrow"):
            return BorrowCreateSerializer
        if self.action in ("return_book_action", "return_legacy"):
            return ReturnBookSerializer
        return BorrowRecordSerializer

    def get_queryset(self):
        qs = BorrowRecord.objects.select_related(
            "book",
            "member",
            "fine",
        )
        user = self.request.user
        if user.role not in (User.Role.ADMIN, User.Role.LIBRARIAN):
            qs = qs.filter(member=user)
        return qs

    def _serialize_record(self, record):
        record = (
            BorrowRecord.objects.select_related("book", "member", "fine")
            .get(pk=record.pk)
        )
        return BorrowRecordSerializer(
            record, context={"request": self.request}
        ).data

    def create(self, request, *args, **kwargs):
        serializer = BorrowCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        record = serializer.save()
        return Response(
            self._serialize_record(record),
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="borrow")
    def borrow(self, request):
        """Legacy alias for POST /api/borrows/."""
        return self.create(request)

    @action(detail=True, methods=["post"], url_path="return")
    def return_book_action(self, request, pk=None):
        record = self.get_object()
        serializer = ReturnBookSerializer(
            data=request.data or {},
            context={"request": request, "borrow_record": record},
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(
            self._serialize_record(updated),
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="return")
    def return_legacy(self, request):
        """Legacy: POST /api/borrows/return/ with borrow_record_id."""
        serializer = ReturnBookSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(
            self._serialize_record(updated),
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="mark-lost",
        permission_classes=[IsAdminOrLibrarian],
    )
    def mark_lost(self, request, pk=None):
        record = self.get_object()
        serializer = MarkLostSerializer(
            data=request.data,
            context={"request": request, "borrow_record": record},
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(self._serialize_record(updated))

    @action(
        detail=True,
        methods=["post"],
        url_path="resolve-lost",
        permission_classes=[IsAdminOrLibrarian],
    )
    def resolve_lost_action(self, request, pk=None):
        record = self.get_object()
        serializer = ResolveLostSerializer(
            data=request.data,
            context={"request": request, "borrow_record": record},
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(self._serialize_record(updated))


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
