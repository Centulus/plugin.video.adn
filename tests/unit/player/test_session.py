"""Playback session: one guid, clock and token chain per run of episodes."""
from types import SimpleNamespace

import pytest

from resources.lib.adn.errors import AdnHttpError
from resources.lib.adn.player_token import PlayerConfiguration
from resources.lib.player import session
from resources.lib.player.session import PlaybackSession


class HomeWindow:
    properties = {}

    def __init__(self, window_id):
        pass

    def setProperty(self, key, value):
        self.properties[key] = value

    def getProperty(self, key):
        return self.properties.get(key, "")


@pytest.fixture
def adn(monkeypatch):
    """Fakes Kodi's home window and ADN's player endpoints; records the calls."""
    HomeWindow.properties = {}
    calls = []
    monkeypatch.setattr(session.xbmcgui, "Window", HomeWindow)
    monkeypatch.setattr(session.player_token, "public_key", lambda _: calls.append("publickey") or "PEM")
    preferences = PlayerConfiguration("CONF", "vf", "sd", False)
    monkeypatch.setattr(
        session.player_token, "configuration", lambda *_: calls.append("configuration") or preferences
    )

    def mint(_, __, refresh):
        calls.append(refresh)
        if refresh == "STALE":
            raise AdnHttpError(401, "/player/refresh/token")
        return SimpleNamespace(header="H", nonce="0" * 16, access="A:" + refresh, refresh=refresh + "+1")

    monkeypatch.setattr(session.player_token, "mint", mint)
    return calls


def opened(video_id=1, profile_id="1", continuing=False):
    return PlaybackSession.open_or_continue(None, video_id, profile_id, continuing=continuing)


def test_a_click_opens_a_new_session(adn):
    assert opened().guid != opened(2).guid
    assert adn == ["publickey", "configuration"] * 2


def test_next_episode_continues_with_the_last_tokens(adn):
    first = opened()
    first.token(1)
    second = opened(2, continuing=True)
    assert second.guid == first.guid
    assert second.token(2).refresh == "CONF+1+1"
    assert adn == ["publickey", "configuration", "CONF", "CONF+1"], "fetched once per session"


@pytest.mark.usefixtures("adn")
def test_another_profile_never_continues_a_session():
    first = opened()
    assert opened(2, "2", continuing=True).guid != first.guid


@pytest.mark.usefixtures("adn")
def test_each_token_leaves_its_access_token_for_the_reports():
    playback = opened()
    playback.token(1)
    assert playback.access_token == "A:CONF"


def test_a_refused_refresh_token_restarts_the_chain_in_the_same_session(adn):
    playback = opened()
    playback._data["refresh_token"] = "STALE"
    playback.token(1)
    assert opened(2, continuing=True).guid == playback.guid
    assert adn == ["publickey", "configuration", "STALE", "configuration", "CONF"]


@pytest.mark.usefixtures("adn")
def test_follow_reads_the_profile_a_choice_is_kept():
    playback = opened()
    assert (playback.language("follow"), playback.quality("follow")) == ("vf", "auto")
    assert (playback.language("vostf"), playback.quality("fhd")) == ("vostf", "fhd")


@pytest.mark.usefixtures("adn")
def test_responsible_mode_imposes_the_profiles_quality():
    playback = opened()
    playback._data["green"] = True
    assert playback.quality("follow") == "sd"


@pytest.fixture
def clock(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(session.time, "time", lambda: now[0])
    return now


@pytest.mark.usefixtures("adn")
def test_viewtime_runs_across_episodes_loading_excepted(clock):
    first = opened()
    clock[0] += 60
    first.loaded(15)
    clock[0] += 30
    assert opened(2, continuing=True).viewtime == 75


@pytest.mark.usefixtures("adn")
def test_a_report_is_due_45_s_after_the_last_one_even_across_episodes(clock):
    first = opened()
    clock[0] += 44
    assert not first.report_due, "the first is due 45 s after the session opened"
    clock[0] += 1
    assert first.report_due
    first.reported()
    clock[0] += 30
    assert not opened(2, continuing=True).report_due
