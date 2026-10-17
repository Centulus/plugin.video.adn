"""Exceptions raised across the add-on."""
from __future__ import annotations


class AdnError(Exception):
    """Base class of the add-on's errors."""


class AdnHttpError(AdnError):
    """The API answered with a non-success status."""

    def __init__(self, status: int, path: str) -> None:
        super().__init__(f"HTTP {status} on {path}")
        self.status = status


class AuthError(AdnError):
    """Login, two-factor or token refresh failed."""


class TwoFactorRequired(AuthError):
    """The password was accepted; a code sent to ``destination`` is still needed."""

    def __init__(self, token: str, destination: str = "") -> None:
        super().__init__("two-factor code required")
        self.token = token
        self.destination = destination


class NotAuthenticated(AuthError):
    """No session; only the login dialog can help."""


class LoginCancelled(AuthError):
    """The user backed out of a login dialog."""
