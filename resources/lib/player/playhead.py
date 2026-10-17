"""Progress reports to ADN, which derives the resume position from them only."""
from __future__ import annotations

from ..adn.api import AdnApi
from ..adn.constants import SAME_DURATION, SOURCE
from ..adn.errors import AdnHttpError
from ..kodi import dialogs
from .session import PlaybackSession


class PlayheadReporter:
    """Sends ``PUT /viewing/history/video/{id}`` for one video of a playback session."""

    def __init__(
        self, api: AdnApi, session: PlaybackSession, video_id: int, duration: int, language: str, quality: str
    ) -> None:
        self._api = api
        self._session = session
        self._video_id = video_id
        self._duration = duration
        self._language = language
        self._quality = quality

    def loading(self, seconds: float) -> None:
        """Count ``seconds`` spent loading the stream, which viewtime leaves out."""
        self._session.loaded(seconds)

    @property
    def due(self) -> bool:
        """A heartbeat is due: 45 s since the session's last report."""
        return self._session.report_due

    def report(self, position: int, player_duration: int = 0) -> None:
        """Report ``position``, unless nothing is played yet or it is past the end."""
        duration = _duration(self._duration, player_duration)
        stoptime = duration if position - 1 == duration else position
        viewtime = self._session.viewtime
        if not (duration > 0 and viewtime > 0 and 0 < stoptime <= duration):
            return
        self._session.reported()
        body = {
            "guid": self._session.guid,
            "viewtime": viewtime,
            "stoptime": stoptime,
            "duration": duration,
            "language": self._language,
            "quality": self._quality,
            "source": SOURCE,
        }
        try:
            self._send(body)
        except Exception as exc:  # never interrupt playback for a report
            dialogs.log(f"progress report failed: {exc}")

    def _send(self, body: dict) -> None:
        """A refused access token (it lasts 3 minutes) gets a new player token, then a resend."""
        try:
            self._api.report_progress(self._video_id, body, self._session.access_token)
        except AdnHttpError as exc:
            if exc.status != 401:
                raise
            self._session.token(self._video_id)
            self._api.report_progress(self._video_id, body, self._session.access_token)


def _duration(announced: int, played: int) -> int:
    """ADN's duration, or the player's when it is known and differs by more than 2 s."""
    if played <= 0:
        return announced
    if abs(played - announced) <= SAME_DURATION:
        return max(played, announced)
    return played
