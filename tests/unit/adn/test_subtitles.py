"""Subtitle decryption, checked by encrypting a WebVTT file the way ADN does."""
import base64
import os
from types import SimpleNamespace

import pytest

from resources.lib.adn import subtitles
from resources.lib.adn.constants import SUBTITLE_KEY_SUFFIX
from resources.lib.adn.errors import AdnError
from resources.lib.vendor import pyaes

WEBVTT = (
    "WEBVTT\n\n"
    "00:00:14.510 --> 00:00:17.220 position:50%,center align:center size:80% line:100%,end\n"
    "<i>Je me pose cette question\ndepuis que je suis petit.</i>\n"
)


def adn_encrypt(text: str, nonce: str, suffix: str = SUBTITLE_KEY_SUFFIX) -> str:
    data = text.encode("utf-8")
    padding = 16 - len(data) % 16
    data += bytes([padding]) * padding
    iv = os.urandom(16)
    cbc = pyaes.AESModeOfOperationCBC(bytes.fromhex(nonce + suffix), iv)
    blocks = b"".join(cbc.encrypt(data[i:i + 16]) for i in range(0, len(data), 16))
    return base64.b64encode(iv).decode() + base64.b64encode(blocks).decode()


def test_decrypts_to_webvtt_and_drops_cue_size():
    nonce = os.urandom(8).hex()
    plain = subtitles.decrypt(adn_encrypt(WEBVTT, nonce), nonce)
    assert plain.startswith("WEBVTT"), plain[:20]
    assert "size:80%" not in plain
    assert "Je me pose cette question" in plain
    assert "position:50%,center align:center line:100%,end" in plain


def test_wrong_nonce_is_an_error_not_garbage():
    encrypted = adn_encrypt(WEBVTT, os.urandom(8).hex())
    with pytest.raises(AdnError):
        subtitles.decrypt(encrypted, os.urandom(8).hex())


def test_fetch_follows_the_location_then_decrypts():
    nonce = os.urandom(8).hex()
    pages = {
        "https://gw/loadbalancer/subtitles/x.webvtt": {"location": "https://subtitle1/x.webvtt"},
        "https://subtitle1/x.webvtt": adn_encrypt(WEBVTT, nonce),
    }
    http = SimpleNamespace(get=lambda url, **__: pages[url])
    assert subtitles.fetch(http, "https://gw/loadbalancer/subtitles/x.webvtt", nonce).startswith("WEBVTT")


def test_fetch_without_location_is_an_error():
    http = SimpleNamespace(get=lambda *_, **__: {})
    with pytest.raises(AdnError):
        subtitles.fetch(http, "https://gw/loadbalancer/subtitles/x.webvtt", "0" * 16)
