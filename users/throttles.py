from rest_framework.throttling import AnonRateThrottle


class AuthRateThrottle(AnonRateThrottle):
    """Tight limit for register / login / password-reset endpoints."""

    scope = "auth"
