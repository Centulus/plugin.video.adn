import pytest

from resources.lib.adn.auth import AuthManager
from resources.lib.adn.errors import AdnHttpError, AuthError, NotAuthenticated, TwoFactorRequired
from resources.lib.adn.http import AdnHttpClient

from ..fakes import FakeResponse, FakeSession


class FakeStore:
    def __init__(self, **values):
        self.username = values.get("username", "")
        self.access_token = values.get("access_token", "")
        self.refresh_token = values.get("refresh_token", "")
        self.profile_id = values.get("profile_id", "1")

    def clear_session(self):
        self.access_token = ""
        self.refresh_token = ""

    def clear_account(self):
        self.clear_session()
        self.profile_id = "1"


def make(responses, **values):
    session = FakeSession(responses)
    store = FakeStore(**values)
    return AuthManager(AdnHttpClient(session), store), store, session


def test_login_stores_tokens_and_signs_the_next_requests():
    session = FakeSession([FakeResponse(200, {"accessToken": "A", "refreshToken": "R"}), FakeResponse(200, {})])
    client, store = AdnHttpClient(session), FakeStore()
    AuthManager(client, store).login("user", "pwd")
    assert (store.access_token, store.refresh_token, store.username) == ("A", "R", "user")
    client.get("/profile")
    assert session.calls[1]["headers"]["authorization"] == "Bearer A"


def test_login_with_2fa_raises_the_challenge_with_masked_email():
    auth, store, _ = make([FakeResponse(200, {"token": "TK", "method": "email", "email": "u***@example.com"})])
    with pytest.raises(TwoFactorRequired) as info:
        auth.login("user", "pwd")
    assert (info.value.token, info.value.destination) == ("TK", "u***@example.com")
    assert store.access_token == "", "no session until the code is verified"


def test_verify_two_factor_stores_tokens():
    auth, store, _ = make([FakeResponse(200, {"accessToken": "A", "refreshToken": "R"})])
    auth.verify_two_factor("TK", "300506")
    assert (store.access_token, store.refresh_token) == ("A", "R")


def test_rejected_credentials_are_an_auth_error():
    auth, _, _ = make([FakeResponse(401, {"message": "invalid credentials"})])
    with pytest.raises(AuthError):
        auth.login("user", "wrong")


def test_server_error_on_login_stays_an_http_error():
    auth, _, _ = make([FakeResponse(503, {})])
    with pytest.raises(AdnHttpError):
        auth.login("user", "pwd")


def test_refresh_keeps_the_new_refresh_token():
    # ADN hands out a new refresh token each time and refuses the old one.
    auth, store, session = make(
        [FakeResponse(200, {"accessToken": "A2", "refreshToken": "R2"})], access_token="A1", refresh_token="R1"
    )
    assert auth.refresh() is True
    assert (store.access_token, store.refresh_token) == ("A2", "R2")
    assert session.calls[0]["body"] == b'{"refreshToken":"R1"}'
    assert list(session.calls[0]["headers"].items())[0] == ("x-access-token", "A1"), "before the common headers"


def test_refused_refresh_forgets_the_session():
    auth, store, _ = make([FakeResponse(401, {})], access_token="A1", refresh_token="R1")
    assert auth.refresh() is False
    assert (store.access_token, store.refresh_token) == ("", "")


def test_no_session_means_not_authenticated():
    auth, _, _ = make([])
    with pytest.raises(NotAuthenticated):
        auth.ensure_authenticated()


def test_logout_forgets_everything_even_if_the_server_fails():
    auth, store, _ = make([FakeResponse(503, {})], username="user", access_token="A", refresh_token="R", profile_id="5")
    auth.logout()
    assert (store.access_token, store.refresh_token, store.profile_id) == ("", "", "1")
    assert auth.is_logged_in is False
