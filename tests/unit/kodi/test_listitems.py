from unittest.mock import MagicMock

import pytest

from resources.lib.adn.models import Show, Video
from resources.lib.kodi import listitems

FAIRY_TAIL_2 = {
    "id": 3629,
    "title": "Fairy Tail - Épisode 2",
    "name": "Le dragon de feu, le singe et le taureau",
    "number": "Épisode 2",
    "shortNumber": "2",
    "season": "1",
    "type": "EPS",
    "duration": 1377,
    "show": {"id": 269, "title": "Fairy Tail"},
}


def video(**changes):
    return Video.from_json({**FAIRY_TAIL_2, **changes})


@pytest.mark.parametrize("kind", ["EPS", "MOV"])
def test_shows_and_movies_are_folders(kind):
    show = Show.from_json({"id": 1, "title": "x", "type": kind})
    assert listitems.show_item(show, "plugin://x/", [])[2] is True


@pytest.mark.parametrize(
    "changes, expected",
    [
        ({}, "1x02. Fairy Tail"),
        ({"season": "3", "shortNumber": "12"}, "3x12. Fairy Tail"),
        ({"season": None}, "02. Fairy Tail"),
        ({"shortNumber": "OAV", "number": "OAV"}, "Fairy Tail - OAV"),
        ({"type": "MOV", "show": {"id": 851, "title": "Akira"}}, "Akira"),
    ],
)
def test_mixed_list_label(changes, expected):
    assert listitems.video_label(video(**changes), mixed=True) == expected


def test_season_page_label():
    assert listitems.video_label(video(), mixed=False) == "Épisode 2 : Le dragon de feu, le singe et le taureau"
    assert listitems.video_label(video(name=""), mixed=False) == "Épisode 2"


def test_playable_entry_typed_video_with_resume_pinned_at_start(monkeypatch):
    item = MagicMock()
    monkeypatch.setattr(listitems.xbmcgui, "ListItem", lambda: item)
    _, built, is_folder = listitems.video_item(video(), "plugin://x/", mixed=True)
    tag = built.getVideoInfoTag.return_value
    assert is_folder is False
    built.setProperty.assert_any_call("IsPlayable", "true")
    tag.setMediaType.assert_called_with("video")
    tag.setResumePoint.assert_called_with(0, 1377)
    tag.setSeason.assert_not_called()


def test_fills_a_given_item_in_place():
    row = MagicMock()
    _, built, _ = listitems.video_item(video(), "plugin://x/", mixed=False, item=row)
    assert built is row
    row.setLabel.assert_called_with("Épisode 2 : Le dragon de feu, le singe et le taureau")


def test_action_entry_runs_and_sorts_last():
    _, item, is_folder = listitems.action_item("Se déconnecter", "plugin://x/", icon="i", plot="p")
    assert is_folder is False
    item.setProperty.assert_any_call("SpecialSort", "bottom")


@pytest.mark.parametrize("seconds, expected", [(5, "0:05"), (315, "5:15"), (3723, "1:02:03")])
def test_clock(seconds, expected):
    assert listitems.clock(seconds) == expected


def test_resolved_item_carries_adn_resume_point():
    item = MagicMock()
    listitems.make_playable(item, "https://cdn/master.m3u8", mimetype="m", subtitles=[], start_at=315, duration=1377)
    item.setPath.assert_called_with("https://cdn/master.m3u8")
    item.getVideoInfoTag.return_value.setResumePoint.assert_called_with(315, 1377)
