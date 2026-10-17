"""ADN endpoints, one method per need, returning models.

``profile`` is any object with ``profile_id`` and ``age_category`` attributes,
read on each call so a profile switch applies at once.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from . import constants
from .errors import AdnError
from .http import AdnHttpClient
from .models import Profile, Rail, Season, Show, Streams, Video

_PARALLEL_CALLS = 8


class AdnApi:
    def __init__(self, http: AdnHttpClient, profile) -> None:
        self._http = http
        self._viewer = profile

    def _profile(self) -> dict:
        return {"x-profile-id": self._viewer.profile_id}

    def _max_age(self) -> str:
        return self._viewer.age_category

    # -- shows ----------------------------------------------------------------

    def home(self) -> list[Rail]:
        params = {"app": constants.HOME_LAYOUT, "maxAgeCategory": self._max_age()}
        data = self._http.get("/show/home", params=params, authed=False)
        return [Rail.from_json(rail) for rail in data.get("home", [])]

    def search(self, query: str) -> list[Show]:
        params = {"search": query, "limit": constants.ALL, "genres": "", "maxAgeCategory": self._max_age()}
        data = self._http.get("/show/catalog", params=params, authed=False)
        return [Show.from_json(show) for show in data.get("shows", [])]

    def recommended(self) -> list[Show]:
        return self._shows("/show/user/recommended")

    def viewing_recommended(self) -> list[Show]:
        return self._shows("/show/user/viewing/recommended")

    def _shows(self, path: str) -> list[Show]:
        params = {"limit": constants.RECOMMENDED_LIMIT, "maxAgeCategory": self._max_age()}
        data = self._http.get(path, params=params, headers=self._profile())
        return [Show.from_json(show) for show in data.get("shows", [])]

    def seasons(self, show_id: int) -> list[Season]:
        data = self._http.get(f"/show/{show_id}/season", params={"order": "asc"}, authed=False)
        return [Season.from_json(season) for season in data.get("seasons", [])]

    def season_counts(self, show_ids) -> dict:
        """``{show_id: number of seasons}``, fetched in parallel; 1 when unknown."""
        unique = list(dict.fromkeys(show_ids))
        with ThreadPoolExecutor(max_workers=_PARALLEL_CALLS) as pool:
            return dict(zip(unique, pool.map(self._season_count, unique)))

    def _season_count(self, show_id: int) -> int:
        try:
            return len(self.seasons(show_id))
        except AdnError:
            return 1

    # -- videos ---------------------------------------------------------------

    def episodes(self, show_id: int, season: str = "") -> list[Video]:
        params = {"offset": 0, "limit": constants.ALL, "order": "asc"}
        if season:
            params["season"] = season
        return self._videos(f"/video/show/{show_id}", params)

    def history(self) -> list[Video]:
        params = {"offset": 0, "limit": constants.HISTORY_LIMIT, "merged": "true", "withNext": "true"}
        return self._videos("/viewing/history", params)

    def watchlist(self) -> list[Video]:
        params = {"offset": 0, "limit": constants.WATCHLIST_LIMIT, "maxAgeCategory": self._max_age()}
        return self._videos("/watchlist", params)

    def _videos(self, path: str, params: dict) -> list[Video]:
        data = self._http.get(path, params=params, headers=self._profile())
        return [Video.from_json(video) for video in data.get("videos", [])]

    # -- account --------------------------------------------------------------

    def profiles(self) -> list[Profile]:
        data = self._http.get("/profile", params={"withPreference": "true"})
        return [Profile.from_json(profile) for profile in data.get("profiles", [])]

    def watchlist_show_ids(self) -> set:
        return {video.show_id for video in self.watchlist()}

    def add_to_watchlist(self, show_id: int) -> None:
        self._http.put(f"/watchlist/show/{show_id}", headers=self._profile())

    def remove_from_watchlist(self, show_id: int) -> None:
        self._http.delete(f"/watchlist/show/{show_id}", headers=self._profile())

    # -- playback -------------------------------------------------------------

    def stream_link(self, video_id: int, player_token: str) -> Streams:
        data = self._http.get(
            f"/player/video/{video_id}/link",
            params=constants.STREAM_LINK_PARAMS,
            call_headers={"x-player-token": player_token},
            authed=False,
        )
        return Streams.from_json(data)

    def report_progress(self, video_id: int, body: dict, access_token: str) -> None:
        """Authenticated by the player access token, not the account's."""
        self._http.put(
            f"/viewing/history/video/{video_id}",
            json=body,
            headers={"x-player-access-token": access_token, **self._profile()},
            authed=False,
        )
