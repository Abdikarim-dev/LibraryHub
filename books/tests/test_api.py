from rest_framework import status
from rest_framework.test import APITestCase

from books.models import Author, Book, Category, Publisher
from users.models import User


def make_user(username, role, password="pass12345"):
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=password,
        role=role,
        email_verified=True,
        is_active=True,
    )
    if role == User.Role.ADMIN:
        user.is_staff = True
        user.save(update_fields=["is_staff"])
    return user


class BooksAPITests(APITestCase):
    def setUp(self):
        self.admin = make_user("admin_books", User.Role.ADMIN)
        self.librarian = make_user("lib_books", User.Role.LIBRARIAN)
        self.member = make_user("mem_books", User.Role.MEMBER)

        self.author = Author.objects.create(
            first_name="Chinua",
            last_name="Achebe",
        )
        self.publisher = Publisher.objects.create(name="Heinemann")
        self.category = Category.objects.create(name="Classic")
        self.book = Book.objects.create(
            title="Things Fall Apart",
            isbn="9780385474542",
            publisher=self.publisher,
            total_copies=5,
            available_copies=5,
        )
        self.book.authors.add(self.author)
        self.book.categories.add(self.category)

    def _login(self, username):
        response = self.client.post(
            "/api/auth/login/",
            {"username": username, "password": "pass12345"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )

    def test_member_can_list_books(self):
        self._login("mem_books")
        response = self.client.get("/api/books/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 1)

    def test_member_cannot_create_book(self):
        self._login("mem_books")
        response = self.client.post(
            "/api/books/",
            {
                "title": "No Access",
                "isbn": "1234567890123",
                "total_copies": 1,
                "available_copies": 1,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_librarian_can_create_book_with_relations(self):
        self._login("lib_books")
        response = self.client.post(
            "/api/books/",
            {
                "title": "Arrow of God",
                "isbn": "9780385014809",
                "publisher": self.publisher.id,
                "author_ids": [self.author.id],
                "category_ids": [self.category.id],
                "total_copies": 2,
                "available_copies": 2,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Arrow of God")
        self.assertEqual(len(response.data["authors_detail"]), 1)
        self.assertTrue(response.data["is_available"])

    def test_available_copies_cannot_exceed_total(self):
        self._login("admin_books")
        response = self.client.post(
            "/api/books/",
            {
                "title": "Bad Stock",
                "isbn": "9999999999999",
                "total_copies": 1,
                "available_copies": 5,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("available_copies", response.data)

    def test_author_publisher_category_crud_permissions(self):
        self._login("lib_books")
        author = self.client.post(
            "/api/authors/",
            {"first_name": "Ngugi", "last_name": "wa Thiong'o"},
            format="json",
        )
        self.assertEqual(author.status_code, status.HTTP_201_CREATED)

        publisher = self.client.post(
            "/api/publishers/",
            {"name": "East African Publishers"},
            format="json",
        )
        self.assertEqual(publisher.status_code, status.HTTP_201_CREATED)

        category = self.client.post(
            "/api/categories/",
            {"name": "Postcolonial"},
            format="json",
        )
        self.assertEqual(category.status_code, status.HTTP_201_CREATED)
        self.assertEqual(category.data["slug"], "postcolonial")

        detail = self.client.get("/api/categories/postcolonial/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)

    def test_unauthenticated_cannot_read(self):
        response = self.client.get("/api/books/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_search_books(self):
        self._login("mem_books")
        response = self.client.get("/api/books/?search=Things")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 1)
