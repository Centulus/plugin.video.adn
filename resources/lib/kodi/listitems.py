"""Kodi list items: menu entries, shows, videos, and container navigation."""
from __future__ import annotations

import xbmc
import xbmcgui
import xbmcplugin

from ..adn.models import Show, Video

# -- list items ---------------------------------------------------------------


def directory_item(label: str, url: str, *, icon: str = "") -> tuple:
    item = xbmcgui.ListItem(label=label)
    if icon:
        item.setArt({"icon": icon, "thumb": icon})
    return url, item, True


def action_item(label: str, url: str, *, icon: str, plot: str) -> tuple:
    """An entry that runs an action: italic, described, always last."""
    item = xbmcgui.ListItem(label=f"[I]{label}[/I]")
    item.setArt({"icon": icon, "thumb": icon})
    item.getVideoInfoTag().setPlot(plot)
    item.setProperty("SpecialSort", "bottom")
    return url, item, False


def show_item(show: Show, url: str, context_menu: list) -> tuple:
    """A series or a movie; a movie's page lists its single video."""
    item = xbmcgui.ListItem(label=show.title)
    item.setArt(_show_art(show))
    tag = item.getVideoInfoTag()
    tag.setTitle(show.title)
    tag.setPlot(show.summary)
    tag.setMediaType("movie" if show.is_movie else "tvshow")
    tag.setGenres(list(show.genres))
    if show.year.isdigit():
        tag.setYear(int(show.year))
    if show.studio:
        tag.setStudios([show.studio])
    item.addContextMenuItems(context_menu)
    return url, item, True


def video_item(
    video: Video,
    url: str,
    *,
    mixed: bool,
    resume_hint: str = "",
    context_menu: list = (),
    item: xbmcgui.ListItem | None = None,
) -> tuple:
    """A playable episode or movie, built in ``item`` when one is given.

    The resume point is pinned at (0, duration): Kodi then neither asks
    "Resume from…" nor uses its own stored position. The resolved item then
    carries ADN's position (see make_playable).
    Episodes are typed "video" without numbers, otherwise skins replace our
    label with their own "Show: SxE. Title".
    """
    if item is None:
        item = xbmcgui.ListItem()
    item.setLabel(video_label(video, mixed=mixed))
    art = _show_art(video.show)
    if video.thumb:
        art.update(thumb=video.thumb, landscape=video.thumb)
    item.setArt(art)
    tag = item.getVideoInfoTag()
    tag.setTitle(video.name or video.number or video.show.title)
    tag.setTvShowTitle(video.show.title)
    tag.setPlot(_video_plot(video, mixed=mixed, resume_hint=resume_hint))
    tag.setDuration(video.duration)
    tag.setGenres(list(video.show.genres))
    tag.setMediaType("movie" if video.is_movie else "video")
    tag.setPlaycount(1 if video.fully_watched else 0)
    if video.duration:
        tag.setResumePoint(0, video.duration)
    item.setProperty("IsPlayable", "true")
    item.addContextMenuItems(list(context_menu))
    return url, item, False


def video_label(video: Video, *, mixed: bool) -> str:
    """"1x02. Charlotte" in lists mixing shows, "Épisode 2 : <title>" on a season page."""
    if video.is_movie:
        return video.show.title or video.title
    if not mixed:
        return f"{video.number} : {video.name}" if video.name else video.number
    if not video.short_number.isdigit():
        return f"{video.show.title} - {video.number}"
    episode = f"{int(video.short_number):02}"
    code = f"{video.season}x{episode}" if video.season else episode
    return f"{code}. {video.show.title}"


def _video_plot(video: Video, *, mixed: bool, resume_hint: str) -> str:
    lines = []
    if mixed and video.name:
        lines.append(f"[B]{video.name}[/B]")
    if resume_hint:
        lines.append(f"[I]{resume_hint}[/I]")
    return "\n".join(lines + [video.summary])


def _show_art(show: Show) -> dict:
    return {
        "poster": show.poster,
        "tvshow.poster": show.poster,
        "thumb": show.poster,
        "fanart": show.carousel or show.thumb,
        "landscape": show.thumb,
        "clearlogo": show.logo,
    }


def clock(seconds: int) -> str:
    """12:34, or 1:02:03 from an hour."""
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"


def make_playable(
    item: xbmcgui.ListItem, path: str, *, mimetype: str, subtitles: list, start_at: float, duration: int
) -> xbmcgui.ListItem:
    """The resolved item; Kodi opens the stream directly at its resume point."""
    item.setPath(path)
    if duration:
        item.getVideoInfoTag().setResumePoint(start_at, duration)
    item.setMimeType(mimetype)
    item.setContentLookup(False)
    if subtitles:
        item.setSubtitles(subtitles)
    return item


def end_directory(handle: int, items: list, *, content: str) -> None:
    xbmcplugin.setContent(handle, content)
    for url, item, is_folder in items:
        xbmcplugin.addDirectoryItem(handle, url, item, is_folder)
    xbmcplugin.endOfDirectory(handle)


# -- navigation ---------------------------------------------------------------


def open_listing(url: str) -> str:
    return f"Container.Update({url})"


def run_action(url: str) -> str:
    return f"RunPlugin({url})"


def refresh() -> None:
    xbmc.executebuiltin("Container.Refresh")
