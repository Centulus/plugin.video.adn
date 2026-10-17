"""Downloads and decrypts ADN subtitles into WebVTT text.

    file  = base64(iv) (24 chars) + base64(ciphertext)
    key   = bytes.fromhex(nonce + SUBTITLE_KEY_SUFFIX), nonce from the player token
    plain = AES-128-CBC(key, iv).decrypt(ciphertext), PKCS#7 padded WebVTT
"""
from __future__ import annotations

import base64
import re

from ..vendor import pyaes
from .constants import SUBTITLE_KEY_SUFFIX
from .errors import AdnError
from .http import AdnHttpClient

_IV_LENGTH = 24
_BLOCK = 16
_CUE_SIZE = re.compile(r"\ssize:[0-9.]+%")


def fetch(http: AdnHttpClient, url: str, nonce: str) -> str:
    """WebVTT text of the subtitles behind a loadbalancer ``url``."""
    location = (http.get(url, authed=False) or {}).get("location")
    if not location:
        raise AdnError(f"no subtitle location at {url!r}")
    return decrypt(http.get(location, authed=False, text=True), nonce)


def decrypt(encrypted: str, nonce: str) -> str:
    iv = base64.b64decode(encrypted[:_IV_LENGTH])
    data = base64.b64decode(encrypted[_IV_LENGTH:])
    if not data or len(data) % _BLOCK:
        raise AdnError("subtitle file is not AES blocks")
    cbc = pyaes.AESModeOfOperationCBC(bytes.fromhex(nonce + SUBTITLE_KEY_SUFFIX), iv)
    plain = b"".join(cbc.decrypt(data[i:i + _BLOCK]) for i in range(0, len(data), _BLOCK))
    padding = plain[-1]
    try:
        if not 1 <= padding <= _BLOCK:
            raise ValueError(padding)
        text = plain[:-padding].decode("utf-8")
    except ValueError as exc:  # UnicodeDecodeError is a ValueError too
        raise AdnError("subtitle decryption failed") from exc
    return _CUE_SIZE.sub("", text)
