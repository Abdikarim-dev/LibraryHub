from django.contrib import admin

from .models import Author, Book, Category, Publisher


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "nationality", "created_at")
    search_fields = ("first_name", "last_name", "nationality")


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "website", "created_at")
    search_fields = ("name", "email")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "isbn",
        "publisher",
        "total_copies",
        "available_copies",
        "published_date",
    )
    list_filter = ("publisher", "categories", "language")
    search_fields = ("title", "isbn")
    filter_horizontal = ("authors", "categories")
