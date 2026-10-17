"""Where to start an HLS stream so playback resumes just before a position.

Kodi only starts on a keyframe, the first one at or after the asked time. So
the position asked is the last keyframe before the resume point, read from
the MPEG-TS segment that holds it.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from .http import AdnHttpClient

_SEGMENT = re.compile(r"#EXTINF:([\d.]+)[^\n]*\n(?:#[^\n]*\n)*([^#\s][^\n]*)")
_TS_PACKET = 188
_PTS_CLOCK = 90000


def keyframe_before(http: AdnHttpClient, master_url: str, position: float) -> float:
    playlist_url = master_url
    playlist = http.get(playlist_url, authed=False, text=True)
    if "#EXTINF" not in playlist:  # a master playlist: its variants share keyframe times
        variant = next(line for line in playlist.splitlines() if line and not line.startswith("#"))
        playlist_url = urljoin(master_url, variant.strip())
        playlist = http.get(playlist_url, authed=False, text=True)
    start, uri = segment_at(playlist, position)
    segment = http.get(urljoin(playlist_url, uri), authed=False, binary=True)
    offsets = [offset for offset in keyframe_offsets(segment) if start + offset <= position]
    return start + max(offsets, default=0.0)


def segment_at(media_playlist: str, position: float) -> tuple:
    """``(start time, uri)`` of the segment holding ``position``."""
    start = 0.0
    segments = [(float(duration), uri.strip()) for duration, uri in _SEGMENT.findall(media_playlist)]
    for duration, uri in segments:
        if start + duration > position:
            return start, uri
        start += duration
    return start - segments[-1][0], segments[-1][1]


def keyframe_offsets(segment: bytes) -> list:
    """Seconds from the segment start to each video keyframe (random access point)."""
    first_pts = None
    offsets = []
    for i in range(0, len(segment) - _TS_PACKET + 1, _TS_PACKET):
        packet = segment[i:i + _TS_PACKET]
        adaptation = (packet[3] >> 4) & 0b10
        payload = (packet[3] >> 4) & 0b01
        if packet[0] != 0x47 or not packet[1] & 0x40 or not payload:
            continue  # no new PES starts here
        body = 4 + (1 + packet[4] if adaptation else 0)
        random_access = adaptation and packet[4] and packet[5] & 0x40
        pes = packet[body:]
        if pes[:3] != b"\x00\x00\x01" or not 0xE0 <= pes[3] <= 0xEF or not pes[7] & 0x80:
            continue  # not a video PES carrying a timestamp
        pts = (pes[9] >> 1 & 7) << 30 | pes[10] << 22 | pes[11] >> 1 << 15 | pes[12] << 7 | pes[13] >> 1
        if first_pts is None:
            first_pts = pts
        if random_access:
            offsets.append((pts - first_pts) / _PTS_CLOCK)
    return offsets
