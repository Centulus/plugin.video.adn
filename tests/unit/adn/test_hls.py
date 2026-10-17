from types import SimpleNamespace

import pytest

from resources.lib.adn import hls

PLAYLIST = """#EXTM3U
#EXT-X-TARGETDURATION:18
#EXTINF:10.0,
s0.ts
#EXTINF:10.0,
s1.ts
#EXTINF:17.5,
s2.ts
#EXT-X-ENDLIST
"""


def video_packet(seconds, keyframe):
    """A TS packet opening a video PES at ``seconds``, flagged random access if ``keyframe``."""
    pts = round(seconds * 90000)
    pes = bytes([0, 0, 1, 0xE0, 0, 0, 0x80, 0x80, 5,
                 0x21 | (pts >> 29 & 0x0E), pts >> 22 & 0xFF, 0x01 | (pts >> 14 & 0xFE),
                 pts >> 7 & 0xFF, 0x01 | (pts << 1 & 0xFE)])
    adaptation = bytes([1, 0x40 if keyframe else 0])
    packet = bytes([0x47, 0x41, 0x00, 0x30]) + adaptation + pes
    return packet + b"\xff" * (188 - len(packet))


def segment(*frames):
    return b"".join(video_packet(seconds, keyframe) for seconds, keyframe in frames)


# A 17.5 s segment starting at 20 s, with keyframes at 0, 2.4 and 7.56 s into it
# (PTS do not start at 0, like real streams).
SEGMENT = segment((1000.0, True), (1001.0, False), (1002.4, True), (1004.0, False), (1007.56, True))


@pytest.mark.parametrize(
    "position, expected",
    [(0, (0.0, "s0.ts")), (15, (10.0, "s1.ts")), (21, (20.0, "s2.ts")), (99, (20.0, "s2.ts"))],
)
def test_segment_at(position, expected):
    assert hls.segment_at(PLAYLIST, position) == expected


def test_keyframe_offsets_are_relative_to_the_segment():
    assert hls.keyframe_offsets(SEGMENT) == pytest.approx([0.0, 2.4, 7.56])


@pytest.mark.parametrize("position, expected", [(21.0, 20.0), (23.0, 22.4), (27.56, 27.56), (30.0, 27.56)])
def test_keyframe_before_never_after_the_position(position, expected):
    pages = {
        "https://cdn/master.m3u8": "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1\nhd/index.m3u8\n",
        "https://cdn/hd/index.m3u8": PLAYLIST,
        "https://cdn/hd/s2.ts": SEGMENT,
    }
    http = SimpleNamespace(get=lambda url, **__: pages[url])
    assert hls.keyframe_before(http, "https://cdn/master.m3u8", position) == pytest.approx(expected)
