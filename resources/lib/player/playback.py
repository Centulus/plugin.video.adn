"""Plays a video: resolves its HLS stream, queues its season, follows playback."""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Callable

import xbmcgui
import xbmcplugin
import xbmcvfs

from ..adn import hls, subtitles
from ..adn.errors import AdnError
from ..context import Context
from ..kodi import dialogs, listitems
from . import monitor, season_queue
from .playhead import PlayheadReporter
from .session import PlaybackSession

_HLS_MIMETYPE = "application/vnd.apple.mpegurl"


@contextmanager
def failing_resolve(handle: int):
    """Tell Kodi the resolve failed if the block raises, so it stops waiting."""
    try:
        yield
    except Exception:
        xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
        raise


def play(ctx: Context, video_id: int, show_id: int, season: str, entry: Callable[..., tuple]) -> None:
    """Play ``video_id``. ``entry(video, item=None)`` builds a season list entry."""
    handle = ctx.router.handle
    settings = ctx.settings
    with failing_resolve(handle):
        monitor.wait_for_previous()
        continuing = season_queue.is_active()
        session = PlaybackSession.open_or_continue(ctx.http, video_id, settings.profile_id, continuing=continuing)
        token = session.token(video_id)
        streams = ctx.api.stream_link(video_id, token.header)
        language, quality, url = streams.pick(session.language(settings.language), session.quality(settings.quality))
        location = _location(ctx, url)

    videos = _season(ctx, show_id, season)
    current = next((video for video in videos if video.id == video_id), None)
    item = entry(current)[1] if current else xbmcgui.ListItem(label=streams.title)
    subtitle = _subtitle_file(ctx, streams.subtitles.get(language), token.nonce, video_id)
    listitems.make_playable(
        item, location, mimetype=_HLS_MIMETYPE, subtitles=[subtitle] if subtitle else [],
        start_at=_start_position(ctx, location, 0 if continuing else streams.resume_at),
        duration=streams.duration,
    )
    xbmcplugin.setResolvedUrl(handle, True, item)

    if current:
        season_queue.queue(videos, current, entry)
    reporter = PlayheadReporter(ctx.api, session, video_id, streams.duration, language, quality)
    monitor.watch(location, reporter)


def _location(ctx: Context, url: str) -> str:
    """The m3u8 URL behind a loadbalancer URL, which answers ``{"location": ...}``."""
    location = (ctx.http.get(url, authed=False) or {}).get("location") if url else ""
    if not location:
        raise AdnError(f"no stream at {url!r}")
    return location


def _start_position(ctx: Context, url: str, position: int) -> float:
    """The keyframe just before ``position``, or ``position`` itself if unknown."""
    if not position:
        return 0
    try:
        return hls.keyframe_before(ctx.http, url, position)
    except Exception as exc:
        dialogs.log(f"keyframe before {position} s unknown: {exc}")
        return position


def _subtitle_file(ctx: Context, url: str, nonce: str, video_id: int) -> str:
    """Local subtitle file, or "" (none for this track, or failed: the video still plays).

    Only this video's decrypted subtitles are kept. They stay until another
    video plays: Kodi may read them again when the playlist comes back to it.
    """
    folder = xbmcvfs.translatePath("special://temp/plugin.video.adn")
    path = os.path.join(folder, f"{video_id}.fr.vtt")  # Kodi reads the language from ".fr"
    _remove_others(folder, path)
    if not url:
        return ""
    try:
        webvtt = subtitles.fetch(ctx.http, url, nonce)
    except Exception as exc:
        dialogs.log(f"subtitles of video {video_id} unavailable: {exc}")
        return ""
    os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        file.write(webvtt)
    return path


def _remove_others(folder: str, kept: str) -> None:
    if not os.path.isdir(folder):
        return
    for entry in os.scandir(folder):
        if entry.path != kept:
            try:
                os.remove(entry.path)
            except OSError as exc:
                dialogs.log(f"could not remove {entry.path}: {exc}")


def _season(ctx: Context, show_id: int, season: str) -> list:
    if not show_id:
        return []
    try:
        return ctx.api.episodes(show_id, season)
    except Exception as exc:
        dialogs.log(f"season of show {show_id} unavailable: {exc}")
        return []
