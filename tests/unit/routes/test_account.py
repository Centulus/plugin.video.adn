"""Sign-in flow, run through routes.run with Kodi's dialogs scripted."""
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from resources.lib import routes
from resources.lib.adn.errors import AuthError, NotAuthenticated, TwoFactorRequired
from resources.lib.adn.models import Profile
from resources.lib.kodi import dialogs, listitems
from resources.lib.routing import Router


@pytest.fixture
def ctx(monkeypatch):
    built = SimpleNamespace(
        router=Router("plugin://plugin.video.adn/", 3),
        query="?action=history",
        auth=MagicMock(),
        api=MagicMock(),
        settings=MagicMock(username=""),
        ended=[],
        answers={},
    )
    built.auth.ensure_authenticated.side_effect = NotAuthenticated("no session")
    built.api.history.return_value = []
    built.api.profiles.return_value = [Profile(id=7, name="centulus", is_main=True)]
    monkeypatch.setattr(routes.xbmcplugin, "endOfDirectory", lambda _, succeeded=True: built.ended.append(succeeded))
    monkeypatch.setattr(listitems, "end_directory", lambda *_, **__: built.ended.append(True))
    monkeypatch.setattr(dialogs, "notify", MagicMock())
    for name in ("ask_text", "ask_password", "ask_number", "confirm"):
        monkeypatch.setattr(dialogs, name, lambda *_, _name=name, **__: built.answers[_name].pop(0))
    return built


def test_first_visit_asks_email_then_password_and_lists(ctx):
    ctx.answers.update(ask_text=["user@mail.fr"], ask_password=["pwd"])
    routes.run(ctx)
    ctx.auth.login.assert_called_once_with("user@mail.fr", "pwd")
    assert ctx.settings.profile_id == 7, "the only profile is picked without asking"
    assert ctx.ended == [True], ctx.ended


def test_a_session_adn_refuses_asks_to_sign_in_then_lists(ctx):
    ctx.auth.ensure_authenticated.side_effect = None  # tokens stored, refused by ADN
    ctx.api.history.side_effect = [NotAuthenticated("session refused"), []]
    ctx.answers.update(ask_text=["user"], ask_password=["pwd"])
    routes.run(ctx)
    ctx.auth.login.assert_called_once_with("user", "pwd")
    assert ctx.ended == [True], ctx.ended


def test_backing_out_of_email_ends_listing_quietly(ctx):
    ctx.answers.update(ask_text=[""])
    routes.run(ctx)  # must not raise: Kodi would show a script error dialog
    assert ctx.ended == [False], ctx.ended
    dialogs.notify.assert_not_called()


def test_wrong_password_offers_retry(ctx):
    ctx.auth.login.side_effect = [AuthError("HTTP 401"), None]
    ctx.answers.update(ask_text=["user", "user"], ask_password=["bad", "good"], confirm=[True])
    routes.run(ctx)
    assert ctx.auth.login.call_count == 2
    assert ctx.ended == [True], ctx.ended


def test_two_factor_code_is_asked_and_verified(ctx):
    ctx.auth.login.side_effect = TwoFactorRequired("TK", "u***@example.com")
    ctx.answers.update(ask_text=["user"], ask_password=["pwd"], ask_number=["300506"])
    routes.run(ctx)
    ctx.auth.verify_two_factor.assert_called_once_with("TK", "300506")
    assert ctx.ended == [True], ctx.ended


def test_wrong_code_then_give_up_cancels_silently(ctx):
    ctx.auth.login.side_effect = TwoFactorRequired("TK")
    ctx.auth.verify_two_factor.side_effect = AuthError("HTTP 400")
    ctx.answers.update(ask_text=["user"], ask_password=["pwd"], ask_number=["1"], confirm=[False])
    routes.run(ctx)
    assert ctx.ended == [False], ctx.ended


def test_every_action_the_code_links_to_has_a_handler():
    lib = Path(routes.__file__).parents[1]
    linked = {
        action
        for path in lib.rglob("*.py")
        for action in re.findall(r'\burl(?:_for)?\(\s*"([a-z_]+)"', path.read_text(encoding="utf-8"))
    }
    assert len(linked) > 10, linked
    assert linked <= set(routes.HANDLERS), linked - set(routes.HANDLERS)
