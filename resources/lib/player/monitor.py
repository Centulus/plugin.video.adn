"""Follows one video while Kodi plays it, reporting progress to ADN.

A report goes out when playback starts, when it goes on after a seek or a
rebuffering, every 45 s while it plays, and when the video stops or Kodi moves
to another one. Pausing reports nothing.
"""
from __future__ import annotations

from typing import Callable

import xbmc
import xbmcgui

from ..kodi import HOME_WINDOW
from .playhead import PlayheadReporter

_POLL = 1  # seconds between two checks
_START_TIMEOUT = 30
_HANDOVER_TIMEOUT = 10
_WATCHING = "plugin.video.adn.watching"
_HANDOVER = "plugin.video.adn.handover"


class _EventPlayer(xbmc.Player):
    """Notes the seeks: a report follows once playback goes on."""

    def __init__(self) -> None:
        super().__init__()
        self.seeked = False
        self.seek_position = None

    def onPlayBackSeek(self, time: int, *_) -> None:
        self.seeked = True
        self.seek_position = time // 1000  # milliseconds

    def onPlayBackSeekChapter(self, *_) -> None:
        self.seeked = True


def wait_for_previous() -> None:
    """Stop following the previous video and wait for its last report.

    Both use the session's single-use tokens. Kodi resolves the next video
    while the previous one still plays, so the previous one is told to stop.
    """
    home, monitor, waited = xbmcgui.Window(HOME_WINDOW), xbmc.Monitor(), 0.0
    if home.getProperty(_WATCHING):
        home.setProperty(_HANDOVER, "1")
    while home.getProperty(_WATCHING) and waited < _HANDOVER_TIMEOUT:
        if monitor.waitForAbort(0.2):
            return
        waited += 0.2


def watch(location: str, reporter: PlayheadReporter) -> None:
    """Block until Kodi stops playing ``location``."""
    home = xbmcgui.Window(HOME_WINDOW)
    home.clearProperty(_HANDOVER)
    home.setProperty(_WATCHING, location)
    try:
        _follow(location, reporter, lambda: not home.getProperty(_HANDOVER))
    finally:
        home.clearProperty(_WATCHING)


def _follow(location: str, reporter: PlayheadReporter, wanted: Callable[[], bool]) -> None:
    player = _EventPlayer()
    monitor = xbmc.Monitor()
    if not _await_start(player, monitor, location, reporter):
        return
    position, duration = _position(player, 0), _duration(player, 0)
    reporter.report(position, duration)
    resumed_report = False
    while not monitor.waitForAbort(_POLL) and _is_mine(player, location) and wanted():
        position, duration = _position(player, position), _duration(player, duration)
        if player.seek_position is not None:  # getTime() can lag behind a seek
            position, player.seek_position = player.seek_position, None
        paused = xbmc.getCondVisibility("Player.Paused")
        if player.seeked:
            player.seeked = False
            resumed_report = resumed_report or not paused
        if xbmc.getCondVisibility("Player.Caching"):
            reporter.loading(_POLL)
            resumed_report = resumed_report or not paused
        elif xbmc.getCondVisibility("Player.Playing") and (resumed_report or reporter.due):
            resumed_report = False
            reporter.report(position, duration)
    reporter.report(position, duration)


def _await_start(player: xbmc.Player, monitor: xbmc.Monitor, location: str, reporter: PlayheadReporter) -> bool:
    """Wait until the stream shows frames; that loading time is left out of viewtime."""
    waited = 0.0
    while not (_is_mine(player, location) and _position(player, 0) > 0):
        if waited >= _START_TIMEOUT or monitor.waitForAbort(0.5):
            return False
        waited += 0.5
    reporter.loading(waited)
    player.seeked = False  # the jump to the resume point
    return True


def _is_mine(player: xbmc.Player, location: str) -> bool:
    """Whether Kodi is playing this stream (paused included)."""
    try:
        return player.isPlaying() and player.getPlayingFile() == location
    except RuntimeError:  # stopped between the two calls
        return False


def _position(player: xbmc.Player, fallback: int) -> int:
    try:
        return int(player.getTime())
    except RuntimeError:
        return fallback


def _duration(player: xbmc.Player, fallback: int) -> int:
    try:
        return int(player.getTotalTime())
    except RuntimeError:
        return fallback
