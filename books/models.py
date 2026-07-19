from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify

from common.models import TimeStampedModel


class Author(TimeStampedModel):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name_plural = "authors"

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def full_name(self):
        return str(self)


class Publisher(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Category(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="children",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Book(TimeStampedModel):
    title = models.CharField(max_length=255)
    isbn = models.CharField(max_length=13, unique=True)
    description = models.TextField(blank=True)
    language = models.CharField(max_length=50, default="English")
    pages = models.PositiveIntegerField(blank=True, null=True)
    published_date = models.DateField(blank=True, null=True)
    cover_image = models.ImageField(
        upload_to="books/covers/",
        blank=True,
        null=True,
    )

    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.PROTECT,
        related_name="books",
        blank=True,
        null=True,
    )
    authors = models.ManyToManyField(
        Author,
        related_name="books",
        blank=True,
    )
    categories = models.ManyToManyField(
        Category,
        related_name="books",
        blank=True,
    )

    total_copies = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(0)],
    )
    available_copies = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        ordering = ["title"]
        indexes = [
            models.Index(fields=["title"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(available_copies__lte=models.F("total_copies")),
                name="book_available_lte_total",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.isbn})"

    @property
    def is_available(self):
        return self.available_copies > 0
