"""The playback session shared by the episodes played in a row.

A click on an episode opens a new session; episodes that follow in the queued
season continue it. It is kept in a property of Kodi's home window, so it
lives in memory for as long as Kodi runs.
"""
from __future__ import annotations

import json
import time
import uuid

import xbmcgui

from ..adn import player_token
from ..adn.constants import PLAYHEAD_INTERVAL, Quality
from ..adn.errors import AdnHttpError
from ..adn.http import AdnHttpClient
from ..kodi import HOME_WINDOW
from ..kodi.settings import FOLLOW

_PROPERTY = "plugin.video.adn.playback_session"


class PlaybackSession:
    """One progress ``guid``, its clocks, and the chain of player tokens."""

    def __init__(self, http: AdnHttpClient, data: dict) -> None:
        self._http = http
        self._data = data

    @classmethod
    def open_or_continue(
        cls, http: AdnHttpClient, video_id: int, profile_id: str, *, continuing: bool
    ) -> PlaybackSession:
        """The current session when ``continuing`` one for this profile, else a new one."""
        data = _load() if continuing else {}
        if data.get("profile_id") != profile_id:
            now = time.time()
            public_key = player_token.public_key(http)
            config = player_token.configuration(http, video_id, profile_id)
            data = {
                "guid": uuid.uuid4().hex,
                "profile_id": profile_id,
                "opened_at": now,
                "loading": 0,
                "reported_at": now,
                "public_key": public_key,
                "refresh_token": config.refresh_token,
                "access_token": "",
                "language": config.language,
                "quality": config.quality,
                "green": config.green,
            }
        session = cls(http, data)
        session.save()
        return session

    @property
    def guid(self) -> str:
        return self._data["guid"]

    @property
    def access_token(self) -> str:
        return self._data["access_token"]

    def language(self, chosen: str) -> str:
        """``chosen``, or with FOLLOW the ADN profile's, read when the session opened."""
        return self._data["language"] if chosen == FOLLOW else chosen

    def quality(self, chosen: str) -> str:
        """``chosen``, or with FOLLOW auto, or the profile's in responsible consumption mode."""
        if chosen != FOLLOW:
            return chosen
        return self._data["quality"] if self._data["green"] else Quality.AUTO

    @property
    def viewtime(self) -> int:
        """Seconds since the session opened, time spent loading the stream excepted."""
        return int(time.time() - self._data["opened_at"] - self._data["loading"])

    def loaded(self, seconds: float) -> None:
        self._data["loading"] += seconds
        self.save()

    @property
    def report_due(self) -> bool:
        """45 s have passed since the last progress report, whatever happened meanwhile."""
        return int(time.time()) >= int(self._data["reported_at"]) + PLAYHEAD_INTERVAL

    def reported(self) -> None:
        self._data["reported_at"] = time.time()
        self.save()

    def token(self, video_id: int) -> player_token.PlayerToken:
        """The next player token; the session keeps the tokens ADN hands back with it.

        If ADN refuses the refresh token (a session left idle too long), the
        chain restarts from the configuration.
        """
        try:
            token = self._mint()
        except AdnHttpError:
            config = player_token.configuration(self._http, video_id, self._data["profile_id"])
            self._data["refresh_token"] = config.refresh_token
            token = self._mint()
        self._data.update(refresh_token=token.refresh, access_token=token.access)
        self.save()
        return token

    def _mint(self) -> player_token.PlayerToken:
        return player_token.mint(self._http, self._data["public_key"], self._data["refresh_token"])

    def save(self) -> None:
        xbmcgui.Window(HOME_WINDOW).setProperty(_PROPERTY, json.dumps(self._data))


def _load() -> dict:
    try:
        return json.loads(xbmcgui.Window(HOME_WINDOW).getProperty(_PROPERTY) or "{}")
    except ValueError:
        return {}
