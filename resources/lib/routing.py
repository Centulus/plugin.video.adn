"""Builds and reads ``plugin://...?action=name&...`` URLs."""
from __future__ import annotations

from urllib.parse import parse_qs, urlencode


class Router:
    def __init__(self, base_url: str, handle: int) -> None:
        self.base_url = base_url
        self.handle = handle  # -1 for actions run from a context menu

    def url_for(self, action: str, **params) -> str:
        query = urlencode({"action": action, **{k: v for k, v in params.items() if v is not None}})
        return f"{self.base_url}?{query}"

    @staticmethod
    def parse(query_string: str) -> tuple:
        """``(action, params)`` of a query string; params are strings."""
        params = {key: values[0] for key, values in parse_qs(query_string.lstrip("?")).items()}
        return params.pop("action", "root"), params
