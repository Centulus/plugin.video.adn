import json
from types import SimpleNamespace

import pytest

from resources.lib.adn.models import Video
from resources.lib.player import season_queue


def season(*numbers):
    return [Video.from_json({"id": n, "number": f"Épisode {n}", "show": {"id": 1425}}) for n in numbers]


class Row:
    def __init__(self, url, label):
        self.url, self.label = url, label


class FakePlaylist:
    """Kodi's video playlist: ``[i]`` is the row itself, swaps apply later."""

    def __init__(self, rows):
        self.rows = list(rows)
        self.pending = []

    def size(self):
        return len(self.rows)

    def add(self, url, item):
        self.rows.append(Row(url, item.label))

    def __getitem__(self, index):
        return self.rows[index]

    def swap_later(self, request):
        params = json.loads(request)["params"]
        self.pending.append((params["position1"], params["position2"]))
        return '{"result": "OK"}'

    def view(self):
        for a, b in self.pending:
            self.rows[a], self.rows[b] = self.rows[b], self.rows[a]
        return [(row.url, row.label) for row in self.rows]


def entry(video, item=None):
    row = item or SimpleNamespace()
    row.label = video.number
    return f"play/{video.id}", row, False


def use_playlist(monkeypatch, playlist):
    monkeypatch.setattr(
        season_queue, "xbmc",
        SimpleNamespace(PlayList=lambda _id: playlist, PLAYLIST_VIDEO=1, executeJSONRPC=playlist.swap_later),
    )


def test_season_queued_around_the_clicked_row(monkeypatch):
    videos = season(1, 2, 3, 4)
    playlist = FakePlaylist([Row("play/3", "Charlotte - Épisode 3")])  # clicked in Resume
    use_playlist(monkeypatch, playlist)
    season_queue.queue(videos, videos[2], entry)
    assert playlist.view() == [
        ("play/1", "Épisode 1"), ("play/2", "Épisode 2"), ("play/3", "Épisode 3"), ("play/4", "Épisode 4"),
    ]


def test_season_not_queued_twice(monkeypatch):
    videos = season(1, 2)
    playlist = FakePlaylist([Row("play/1", "Épisode 1"), Row("play/2", "Épisode 2")])
    use_playlist(monkeypatch, playlist)
    season_queue.queue(videos, videos[1], pytest.fail)
    assert playlist.view() == [("play/1", "Épisode 1"), ("play/2", "Épisode 2")]
