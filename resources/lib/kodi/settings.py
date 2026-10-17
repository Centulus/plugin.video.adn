"""The add-on's Kodi settings: user preferences, session and active profile."""
from __future__ import annotations

import xbmcaddon

FOLLOW = "follow"


class _Setting:
    """A string setting exposed as an attribute; ``default`` stands in for empty.

    Each access goes through a fresh ``xbmcaddon.Addon()``. An instance keeps
    its own copy of all settings and saves the whole copy on any write, so a
    long-lived one (a playback being followed) would put back values the
    user changed meanwhile.
    """

    def __init__(self, key: str, default: str = "") -> None:
        self.key = key
        self.default = default

    def __get__(self, settings, _owner=None):
        if settings is None:  # accessed on the class itself
            return self
        return xbmcaddon.Addon().getSetting(self.key) or self.default

    def __set__(self, settings, value) -> None:
        xbmcaddon.Addon().setSetting(self.key, str(value or ""))


class Settings:
    username = _Setting("adn_username")
    access_token = _Setting("access_token")
    refresh_token = _Setting("refresh_token")

    profile_id = _Setting("profile_id", "1")
    profile_name = _Setting("profile_name")
    age_category = _Setting("age_category", "18")
    language = _Setting("preferred_language", FOLLOW)
    quality = _Setting("preferred_quality", FOLLOW)

    def clear_session(self) -> None:
        self.access_token = ""
        self.refresh_token = ""

    def clear_account(self) -> None:
        """Sign-out: forget session and profile, keep the username to prefill the login."""
        self.clear_session()
        self.profile_id = ""
        self.profile_name = ""
        self.age_category = ""
