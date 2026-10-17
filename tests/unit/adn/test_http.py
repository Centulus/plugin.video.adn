import pytest

from resources.lib.adn import constants
from resources.lib.adn.errors import AdnHttpError, NotAuthenticated
from resources.lib.adn.http import AdnHttpClient

from ..fakes import FakeResponse, FakeSession


def test_relative_path_is_prefixed_absolute_is_kept():
    session = FakeSession([FakeResponse(200, {}), FakeResponse(200, {})])
    client = AdnHttpClient(session)
    client.get("/show/home")
    client.get("https://cdn.example/x.m3u8")
    assert session.calls[0]["url"] == constants.BASE_URL + "/show/home"
    assert session.calls[1]["url"] == "https://cdn.example/x.m3u8"


def test_401_triggers_single_refresh_then_retries():
    session = FakeSession([FakeResponse(401), FakeResponse(200, {"ok": True})])
    client = AdnHttpClient(session)
    refreshed = []
    client.on_unauthorized = lambda: (refreshed.append(True), True)[1]
    assert client.get("/user") == {"ok": True}
    assert len(refreshed) == 1, "refresh should run exactly once"
    assert len(session.calls) == 2


def test_a_session_adn_refuses_asks_for_a_sign_in():
    session = FakeSession([FakeResponse(401)])
    client = AdnHttpClient(session)
    client.on_unauthorized = lambda: False
    with pytest.raises(NotAuthenticated):
        client.get("/user")


def test_a_public_call_answering_401_is_a_plain_http_error():
    session = FakeSession([FakeResponse(401)])
    with pytest.raises(AdnHttpError) as info:
        AdnHttpClient(session).post("/player/refresh/token", authed=False)
    assert info.value.status == 401


def test_text_mode_returns_raw_body():
    session = FakeSession([FakeResponse(200, text="-----BEGIN PUBLIC KEY-----")])
    client = AdnHttpClient(session)
    assert client.get("/player/publickey", authed=False, text=True).startswith("-----BEGIN")


def test_empty_body_returns_none():
    session = FakeSession([FakeResponse(200, text="")])
    client = AdnHttpClient(session)
    assert client.put("/user/lastvisit") is None


def test_headers_are_exact_and_in_order():
    session = FakeSession([FakeResponse(200, {})])
    client = AdnHttpClient(session)
    client.auth_headers = lambda: {"authorization": "Bearer T"}
    client.get("/watchlist", headers={"x-profile-id": "1"})
    assert list(session.calls[0]["headers"].items()) == [
        ("x-source", "AndroidTV"),
        ("accept-language", "fr"),
        ("origin", "adn-android"),
        ("authorization", "Bearer T"),
        ("x-profile-id", "1"),
        ("accept-encoding", "gzip"),
        ("user-agent", "okhttp/4.12.0"),
        ("cookie", "aws-waf-token=no valid token"),
    ]


def test_a_calls_own_headers_go_before_the_common_ones():
    session = FakeSession([FakeResponse(200, {})])
    AdnHttpClient(session).post(
        "/player/refresh/token", call_headers={"x-player-refresh-token": "RT"}, authed=False
    )
    assert list(session.calls[0]["headers"]) == [
        "x-player-refresh-token", "x-source", "accept-language", "origin", "content-length",
        "accept-encoding", "user-agent", "cookie",
    ]


def test_json_body_is_compact_utf8_with_its_length():
    session = FakeSession([FakeResponse(200, {})])
    AdnHttpClient(session).post("/authentication/login", json={"username": "u", "support2FA": True}, authed=False)
    call = session.calls[0]
    assert call["body"] == b'{"username":"u","support2FA":true}'
    assert list(call["headers"]) == [
        "x-source", "accept-language", "origin", "content-type", "content-length",
        "accept-encoding", "user-agent", "cookie",
    ]
    assert call["headers"]["content-type"] == "application/json; charset=UTF-8"
    assert call["headers"]["content-length"] == str(len(call["body"]))


def test_bodyless_put_announces_zero_length_get_does_not():
    session = FakeSession([FakeResponse(200, text=""), FakeResponse(200, {})])
    client = AdnHttpClient(session)
    client.put("/watchlist/show/1")
    client.get("/show/home", authed=False)
    assert session.calls[0]["headers"]["content-length"] == "0"
    assert "content-length" not in session.calls[1]["headers"]
    assert "authorization" not in session.calls[1]["headers"]
