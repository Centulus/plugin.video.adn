import base64
import json

from resources.lib.adn import player_token
from resources.lib.vendor import rsa

PUBLIC_KEY, PRIVATE_KEY = rsa.newkeys(1024)


def openssl_pem(public_key) -> str:
    """``public_key`` in the format /player/publickey serves: X.509 "BEGIN PUBLIC KEY"."""
    from pyasn1.codec.der import encoder
    from pyasn1.type import univ
    from rsa.asn1 import OpenSSLPubKey

    info = OpenSSLPubKey()
    info["header"]["oid"] = univ.ObjectIdentifier("1.2.840.113549.1.1.1")  # rsaEncryption
    info["header"]["parameters"] = univ.Null("")
    info["key"] = b"\x00" + public_key.save_pkcs1("DER")  # bit string with no unused bits
    return rsa.pem.save_pem(encoder.encode(info), "PUBLIC KEY").decode()


PEM = openssl_pem(PUBLIC_KEY)


class FakeHttp:
    def __init__(self):
        self.calls = []

    def get(self, path, **__):
        self.calls.append(path)
        if path == "/player/publickey":
            return PEM
        options = {"user": {"refreshToken": "RT"}, "preference": {"language": "vf", "quality": "sd", "green": True}}
        return {"player": {"options": options}}

    def post(self, path, call_headers=None, **__):
        self.calls.append((path, call_headers))
        return {"token": "PLAYER_T", "accessToken": "ACCESS", "refreshToken": "RT2"}


def test_session_parts_come_from_publickey_and_configuration():
    http = FakeHttp()
    assert player_token.public_key(http) == PEM
    assert player_token.configuration(http, 3628, "1") == ("RT", "vf", "sd", True)
    assert http.calls == ["/player/publickey", "/player/video/3628/configuration"]


def test_header_carries_minted_token_and_returned_nonce():
    http = FakeHttp()
    token = player_token.mint(http, PEM, "RT")
    payload = json.loads(rsa.decrypt(base64.b64decode(token.header), PRIVATE_KEY))
    assert payload == {"k": token.nonce, "t": "PLAYER_T"}, payload
    assert len(token.nonce) == 16, token.nonce
    assert http.calls == [("/player/refresh/token", {"x-player-refresh-token": "RT"})]
    assert (token.access, token.refresh) == ("ACCESS", "RT2"), "for the reports, and for the next call"


def test_each_token_has_a_fresh_nonce():
    assert player_token.mint(FakeHttp(), PEM, "RT").nonce != player_token.mint(FakeHttp(), PEM, "RT").nonce
