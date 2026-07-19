from rest_framework.routers import DefaultRouter

from .views import AuthorViewSet, BookViewSet, CategoryViewSet, PublisherViewSet

router = DefaultRouter()
router.register(r"authors", AuthorViewSet, basename="authors")
router.register(r"publishers", PublisherViewSet, basename="publishers")
router.register(r"categories", CategoryViewSet, basename="categories")
router.register(r"books", BookViewSet, basename="books")

urlpatterns = router.urls
