"""HTTP access to the ADN gateway: exact headers in their order, compact JSON."""
from __future__ import annotations

import json as jsonlib
from typing import Callable

import requests
from requests.structures import CaseInsensitiveDict

from . import constants
from .errors import AdnHttpError, NotAuthenticated

# A call's own headers come first, then these, the session's, then the trailing ones.
_LEADING = ("x-source", "accept-language", "origin")
_TRAILING = ("accept-encoding", "user-agent", "cookie")
_JSON = "application/json; charset=UTF-8"


class AdnHttpClient:
    """``auth_headers`` and ``on_unauthorized`` are set by the AuthManager."""

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or requests.Session()
        self.auth_headers: Callable[[], dict] = dict
        self.on_unauthorized: Callable[[], bool] = lambda: False

    def get(self, path: str, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs):
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs):
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs):
        return self.request("DELETE", path, **kwargs)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        headers: dict | None = None,
        call_headers: dict | None = None,
        authed: bool = True,
        text: bool = False,
        binary: bool = False,
    ):
        """Decoded JSON body (raw text or bytes with ``text``/``binary``), ``None`` when empty.

        ``path`` is gateway-relative or an absolute URL. ``call_headers`` go before the
        common headers, ``headers`` after them.
        """
        url = path if path.startswith("http") else constants.BASE_URL + path
        body = jsonlib.dumps(json, separators=(",", ":")).encode() if json is not None else None
        sent = (method, url, params, body, call_headers or {}, headers or {}, authed)
        response = self._send(*sent)
        if response.status_code == 401 and authed:
            if not self.on_unauthorized():
                raise NotAuthenticated(f"session refused on {path}")
            response = self._send(*sent)
        if not response.ok:
            raise AdnHttpError(response.status_code, path)
        if text:
            return response.text
        if binary:
            return response.content
        return response.json() if response.content else None

    def _send(self, method, url, params, body, call_headers, headers, authed):
        prepared = self._session.prepare_request(requests.Request(method, url, params=params, data=body))
        prepared.headers = CaseInsensitiveDict(self._headers(method, body, call_headers, headers, authed))
        return self._session.send(prepared)

    def _headers(self, method: str, body: bytes | None, first: dict, extra: dict, authed: bool) -> dict:
        common = constants.COMMON_HEADERS
        headers = dict(first)
        headers.update({name: common[name] for name in _LEADING})
        if authed:
            headers.update(self.auth_headers())
        headers.update(extra)
        if body is not None:
            headers["content-type"] = _JSON
        if body is not None or method in ("POST", "PUT"):
            headers["content-length"] = str(len(body or b""))
        headers.update({name: common[name] for name in _TRAILING})
        return headers
