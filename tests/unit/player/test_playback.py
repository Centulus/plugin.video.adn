from types import SimpleNamespace

import pytest

from resources.lib.adn.errors import AdnError
from resources.lib.adn.models import Streams, Video
from resources.lib.player import playback


def season(*numbers):
    return [Video.from_json({"id": n, "number": f"Épisode {n}", "show": {"id": 1425}}) for n in numbers]


def entry(video, item=None):
    row = item or SimpleNamespace()
    row.label = video.number
    return f"play/{video.id}", row, False


@pytest.fixture
def played(monkeypatch):
    """Runs playback.play with Kodi and the network faked; returns what it did."""
    done = SimpleNamespace(resolved=[], reporters=[], started_at=[])
    monkeypatch.setattr(playback.xbmcplugin, "setResolvedUrl", lambda *args: done.resolved.append(args[2]))
    token = SimpleNamespace(header="H", nonce="0" * 16, access="A", refresh="RT2")
    monkeypatch.setattr(
        playback.PlaybackSession, "open_or_continue",
        lambda *_, **__: SimpleNamespace(
            guid="GUID", token=lambda _: token, language=lambda chosen: chosen, quality=lambda chosen: chosen
        ),
    )
    queued = []
    monkeypatch.setattr(playback.season_queue, "is_active", lambda: bool(queued))
    monkeypatch.setattr(playback.monitor, "wait_for_previous", lambda: None)
    monkeypatch.setattr(playback.season_queue, "queue", lambda *_: None)
    monkeypatch.setattr(playback, "_location", lambda *_: "https://cdn/master.m3u8")
    monkeypatch.setattr(
        playback.listitems, "make_playable", lambda *_, start_at, **__: done.started_at.append(start_at)
    )
    monkeypatch.setattr(playback, "_start_position", lambda _, __, position: position)
    monkeypatch.setattr(playback.monitor, "watch", lambda _, reporter: done.reporters.append(reporter))

    def play(streams, quality="auto", reached_by_next=False):
        queued.extend([reached_by_next] if reached_by_next else [])
        context = SimpleNamespace(
            http=None,
            router=SimpleNamespace(handle=3),
            settings=SimpleNamespace(profile_id="1", language="vostf", quality=quality),
            api=SimpleNamespace(stream_link=lambda *_: streams, episodes=lambda *_: season(1, 2)),
        )
        playback.play(context, 2, 1425, "1", entry)
        return done

    return play


def test_failing_resolve_tells_kodi_and_reraises(monkeypatch):
    calls = []
    monkeypatch.setattr(playback.xbmcplugin, "setResolvedUrl", lambda *args: calls.append(args[1]))
    with pytest.raises(ValueError), playback.failing_resolve(7):
        raise ValueError("boom")
    with playback.failing_resolve(7):
        pass
    assert calls == [False], calls


def test_resolves_the_season_entry_and_reports_what_it_plays(played):
    # Only sd/auto exist for this video: the user's 1080p falls back to auto.
    done = played(Streams(duration=1439, by_language={"vostf": {"sd": "lb-sd", "auto": "lb-auto"}}), quality="fhd")
    assert done.resolved[0].label == "Épisode 2", done.resolved
    reporter = done.reporters[0]
    assert (reporter._session.guid, reporter._language, reporter._quality) == ("GUID", "vostf", "auto")


def test_a_clicked_video_starts_at_adns_position_a_next_one_from_the_start(played):
    streams = Streams(duration=1440, current_time=600, by_language={"vostf": {"auto": "lb"}})
    assert played(streams).started_at == [600]
    assert played(streams, reached_by_next=True).started_at == [600, 0]


def test_only_the_playing_videos_decrypted_subtitles_are_kept(monkeypatch, tmp_path):
    for name in ("1.fr.vtt", "2.fr.vtt"):
        (tmp_path / name).write_text("old", encoding="utf-8")
    monkeypatch.setattr(playback.xbmcvfs, "translatePath", lambda _: str(tmp_path))
    monkeypatch.setattr(playback.subtitles, "fetch", lambda *_: "WEBVTT")
    ctx = SimpleNamespace(http=None)
    assert playback._subtitle_file(ctx, "lb-sub", "0" * 16, 2) == str(tmp_path / "2.fr.vtt")
    assert [(f.name, f.read_text(encoding="utf-8")) for f in tmp_path.iterdir()] == [("2.fr.vtt", "WEBVTT")]
    assert playback._subtitle_file(ctx, "", "0" * 16, 3) == ""
    assert list(tmp_path.iterdir()) == [], "a video without subtitles leaves none behind"


def test_a_stream_without_location_is_an_error():
    ctx = SimpleNamespace(http=SimpleNamespace(get=lambda *_, **__: {}))
    with pytest.raises(AdnError):
        playback._location(ctx, "https://gw/loadbalancer/video.m3u8")
