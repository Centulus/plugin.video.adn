"""Queues a season around the clicked episode, for next/previous and auto-advance."""
from __future__ import annotations

import json
from typing import Callable

import xbmc

from ..kodi import dialogs


def queue(videos: list, current, entry: Callable[..., tuple]) -> None:
    """Fill Kodi's one-row playlist with the rest of ``current``'s season.

    Kodi starts a click as a one-row playlist holding a copy of the clicked
    list entry. That row is relabelled like the others, then the rest is
    appended and the row is swapped down to its place in the season: JSON-RPC
    ``Playlist.Swap`` keeps the player in sync, ``PlayList.add`` at an index
    does not. Kodi applies swaps later, so the row is relabelled first.
    ``entry(video, item=None)`` builds a row, or fills ``item`` in place.
    """
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    if playlist.size() != 1:
        return  # already playing through a queued season
    entry(current, playlist[0])
    index = videos.index(current)
    for video in videos[:index] + videos[index + 1:]:
        url, item, _ = entry(video)
        playlist.add(url, item)
    for position in range(index):
        response = _json_rpc(
            "Playlist.Swap", {"playlistid": xbmc.PLAYLIST_VIDEO, "position1": position, "position2": position + 1}
        )
        if '"error"' in response:
            dialogs.log(f"Playlist.Swap failed: {response}")
            return


def is_active() -> bool:
    """Whether Kodi is playing through a queued season."""
    return xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() > 1


def _json_rpc(method: str, params: dict) -> str:
    return xbmc.executeJSONRPC(json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}))
