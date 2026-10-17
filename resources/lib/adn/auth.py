"""Login, two-factor, token storage and refresh.

The password is only sent at login, never stored: the long-lived refresh token
keeps the session alive. ``store`` is any object with ``username``,
``access_token`` and ``refresh_token`` attributes and ``clear_session()`` /
``clear_account()`` methods (the add-on settings in Kodi).
"""
from __future__ import annotations

from . import constants
from .errors import AdnHttpError, AuthError, NotAuthenticated, TwoFactorRequired
from .http import AdnHttpClient


class AuthManager:
    def __init__(self, http: AdnHttpClient, store) -> None:
        self._http = http
        self._store = store
        http.auth_headers = self._headers
        http.on_unauthorized = self.refresh

    def _headers(self) -> dict:
        token = self._store.access_token
        return {"authorization": f"Bearer {token}"} if token else {}

    @property
    def is_logged_in(self) -> bool:
        return bool(self._store.access_token or self._store.refresh_token)

    def login(self, username: str, password: str) -> None:
        """Sign in; raise TwoFactorRequired when the account needs a code."""
        body = {"username": username, "password": password, "source": constants.SOURCE, "support2FA": True}
        data = self._post_credentials("/authentication/login", body)
        self._store.username = username
        if not data.get("accessToken"):
            destination = data.get("email") or data.get("phoneNumber") or ""
            raise TwoFactorRequired(data.get("token") or "", destination)
        self._save_tokens(data)

    def verify_two_factor(self, token: str, code: str) -> None:
        body = {"token": token, "code": code, "source": constants.SOURCE}
        data = self._post_credentials("/authentication/2fa/verify", body)
        if not data.get("accessToken"):
            raise AuthError("two-factor code rejected")
        self._save_tokens(data)

    def _post_credentials(self, path: str, body: dict) -> dict:
        """A 4xx on a login step means the server refused what the user typed."""
        try:
            return self._http.post(path, json=body, authed=False) or {}
        except AdnHttpError as exc:
            if 400 <= exc.status < 500:
                raise AuthError(f"{path} rejected (HTTP {exc.status})") from exc
            raise

    def refresh(self) -> bool:
        """Mint a new access token; False (and session forgotten) if it fails."""
        if not self._store.refresh_token:
            return False
        try:
            data = self._http.post(
                "/authentication/refresh",
                json={"refreshToken": self._store.refresh_token},
                call_headers={"x-access-token": self._store.access_token},
                authed=False,
            )
        except Exception:
            self._store.clear_session()
            return False
        self._save_tokens(data)
        return True

    def ensure_authenticated(self) -> None:
        if self._store.access_token:
            return
        if not self.refresh():
            raise NotAuthenticated("no session")

    def logout(self) -> None:
        """Revoke the session server-side when possible, then forget the account."""
        if self._store.refresh_token:
            try:
                self._http.post(
                    "/authentication/logout",
                    json={"refreshToken": self._store.refresh_token},
                    call_headers={"x-access-token": self._store.access_token},
                    authed=False,
                )
            except Exception:
                pass  # forgotten locally either way
        self._store.clear_account()

    def _save_tokens(self, data: dict) -> None:
        self._store.access_token = data.get("accessToken") or ""
        self._store.refresh_token = data.get("refreshToken") or ""
