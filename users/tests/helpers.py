from users.models import User


def make_user(
    *,
    username,
    email=None,
    password="Pass12345!",
    role=User.Role.MEMBER,
    email_verified=True,
    is_active=True,
    **extra,
):
    user = User.objects.create_user(
        username=username,
        email=email or f"{username}@example.com",
        password=password,
        role=role,
        **extra,
    )
    user.email_verified = email_verified
    user.is_active = is_active
    if role == User.Role.ADMIN:
        user.is_staff = True
    user.save()
    return user
