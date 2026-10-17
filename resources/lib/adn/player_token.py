"""The ``X-Player-Token`` header the stream link requires.

    t     = token from POST /player/refresh/token
    k     = 8 random bytes, hex (nonce, also half of the subtitle key)
    token = base64(RSA-PKCS1v1.5({"k": k, "t": t}, public key from /player/publickey))

The public key and the configuration are fetched once per playback session.
Each POST /player/refresh/token answers with a new player refresh token, to
send on the next call (the one just used is no longer valid), and an access
token for the progress reports, valid 3 minutes.
"""
from __future__ import annotations

import base64
import json
import os
from typing import NamedTuple

from ..vendor import rsa
from .constants import Language, Quality
from .http import AdnHttpClient


class PlayerToken(NamedTuple):
    header: str
    nonce: str
    access: str
    refresh: str


class PlayerConfiguration(NamedTuple):
    refresh_token: str
    language: str
    quality: str
    green: bool  # "consommation responsable"


def public_key(http: AdnHttpClient) -> str:
    """PEM of the key the token is encrypted with."""
    return http.get("/player/publickey", authed=False, text=True)


def configuration(http: AdnHttpClient, video_id: int, profile_id: str) -> PlayerConfiguration:
    config = http.get(f"/player/video/{video_id}/configuration", headers={"x-profile-id": profile_id})
    options = config["player"]["options"]
    preference = options.get("preference") or {}
    return PlayerConfiguration(
        options["user"]["refreshToken"],
        preference.get("language") or Language.DEFAULT,
        preference.get("quality") or Quality.DEFAULT,
        bool(preference.get("green")),
    )


def mint(http: AdnHttpClient, public_key_pem: str, refresh: str) -> PlayerToken:
    minted = http.post("/player/refresh/token", call_headers={"x-player-refresh-token": refresh}, authed=False)
    nonce = os.urandom(8).hex()
    payload = json.dumps({"k": nonce, "t": minted["token"]}, separators=(",", ":"))
    key = rsa.PublicKey.load_pkcs1_openssl_pem(public_key_pem.encode())
    header = base64.b64encode(rsa.encrypt(payload.encode(), key)).decode()
    return PlayerToken(header, nonce, minted["accessToken"], minted.get("refreshToken") or refresh)
