from rest_framework.routers import DefaultRouter

from .views import BorrowRecordViewSet, FineViewSet

router = DefaultRouter()
router.register(r"borrows", BorrowRecordViewSet, basename="borrows")
router.register(r"fines", FineViewSet, basename="fines")

urlpatterns = router.urls
