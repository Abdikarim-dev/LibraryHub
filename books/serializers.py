from rest_framework import serializers

from common.image_validation import validate_uploaded_image

from .models import Author, Book, Category, Publisher
from .services import create_book, update_book


class AuthorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Author
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "bio",
            "nationality",
            "date_of_birth",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = [
            "id",
            "name",
            "website",
            "address",
            "email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "parent",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]

    def validate_name(self, value):
        qs = Category.objects.filter(name__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A category with this name already exists."
            )
        return value


class BookListSerializer(serializers.ModelSerializer):
    authors = AuthorSerializer(many=True, read_only=True)
    publisher_name = serializers.CharField(
        source="publisher.name",
        read_only=True,
        allow_null=True,
    )
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "isbn",
            "language",
            "publisher",
            "publisher_name",
            "authors",
            "total_copies",
            "available_copies",
            "is_available",
            "published_date",
        ]


class BookSerializer(serializers.ModelSerializer):
    authors_detail = AuthorSerializer(
        source="authors",
        many=True,
        read_only=True,
    )
    categories_detail = CategorySerializer(
        source="categories",
        many=True,
        read_only=True,
    )
    publisher_detail = PublisherSerializer(
        source="publisher",
        read_only=True,
    )
    author_ids = serializers.PrimaryKeyRelatedField(
        source="authors",
        many=True,
        queryset=Author.objects.all(),
        write_only=True,
        required=False,
    )
    category_ids = serializers.PrimaryKeyRelatedField(
        source="categories",
        many=True,
        queryset=Category.objects.all(),
        write_only=True,
        required=False,
    )
    is_available = serializers.BooleanField(read_only=True)
    cover_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "isbn",
            "description",
            "language",
            "pages",
            "published_date",
            "cover_image",
            "publisher",
            "publisher_detail",
            "author_ids",
            "authors_detail",
            "category_ids",
            "categories_detail",
            "total_copies",
            "available_copies",
            "is_available",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "available_copies",
            "created_at",
            "updated_at",
        ]

    def validate_cover_image(self, value):
        return validate_uploaded_image(value)

    def create(self, validated_data):
        return create_book(validated_data=validated_data)

    def update(self, instance, validated_data):
        return update_book(book=instance, validated_data=validated_data)
