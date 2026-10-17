"""Test doubles for the HTTP layer."""
from __future__ import annotations

import json as _json

import requests


class FakeResponse:
    def __init__(self, status=200, body=None, text=""):
        self.status_code = status
        self.ok = 200 <= status < 300
        self._body = body
        self.text = text or (_json.dumps(body) if body is not None else "")
        self.content = self.text.encode()

    def json(self):
        return self._body


class FakeSession(requests.Session):
    """Returns queued responses and records the prepared requests it was sent."""

    def __init__(self, responses):
        super().__init__()
        self._responses = list(responses)
        self.calls = []

    def send(self, prepared, **__):
        self.calls.append(
            {"method": prepared.method, "url": prepared.url, "headers": prepared.headers, "body": prepared.body}
        )
        return self._responses.pop(0)
