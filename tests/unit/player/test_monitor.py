"""monitor.watch against a scripted player: one tick per second of Kodi time."""
from types import SimpleNamespace

from resources.lib.adn.constants import PLAYHEAD_INTERVAL
from resources.lib.player import monitor

STREAM = "https://cdn.example/master.m3u8"


class HomeWindow:
    """Kodi's home window properties, shared by every instance."""

    properties = {}

    def __init__(self, _=None):
        pass

    def getProperty(self, key):
        return self.properties.get(key, "")

    def setProperty(self, key, value):
        self.properties[key] = value

    def clearProperty(self, key):
        self.properties.pop(key, None)


class ScriptedPlayer:
    """Plays ``positions`` one per tick, then stops, firing Kodi's seek callback.

    ``paused`` and ``caching``: ticks in that state. ``seeks``: ticks a seek lands on.
    """

    def __init__(self, positions, paused=(), caching=(), seeks=(), switch_at=None, next_resolved_at=None):
        self.positions = list(positions)
        self.paused = set(paused)
        self.caching = set(caching)
        self.seeks = set(seeks)
        self.switch_at = switch_at
        self.next_resolved_at = next_resolved_at
        self.tick = 0
        self.seeked = False
        self.seek_position = None

    def advance(self):
        self.tick += 1
        if self.tick == self.next_resolved_at:  # what wait_for_previous asks
            HomeWindow.properties["plugin.video.adn.handover"] = "1"
        if self.tick in self.seeks:
            self.seeked, self.seek_position = True, self.positions[self.tick]

    def isPlaying(self):
        return self.tick < len(self.positions)

    def getPlayingFile(self):
        if self.switch_at is not None and self.tick >= self.switch_at:
            return "https://cdn.example/next-episode.m3u8"
        return STREAM

    def getTime(self):
        if not self.isPlaying():
            raise RuntimeError("Kodi is not playing any media file")
        return float(self.positions[self.tick])

    def getTotalTime(self):
        return 1440.0

    def condition(self, name):
        if not self.isPlaying():
            return False
        paused, caching = self.tick in self.paused, self.tick in self.caching
        return {"Player.Paused": paused, "Player.Caching": caching}.get(name, not (paused or caching))


class Reporter:
    """Records reported positions; a heartbeat is due 45 ticks after the last report."""

    def __init__(self, player):
        self.player = player
        self.reports = []
        self.loaded = 0
        self.last = 0

    def loading(self, seconds):
        self.loaded += seconds

    @property
    def due(self):
        return self.player.tick - self.last >= PLAYHEAD_INTERVAL

    def report(self, position, duration):
        assert duration == 1440
        self.last = self.player.tick
        self.reports.append(position)


def watch(monkeypatch, player):
    HomeWindow.properties = {}
    monkeypatch.setattr(monitor.xbmcgui, "Window", HomeWindow)
    monkeypatch.setattr(monitor, "_EventPlayer", lambda: player)
    monkeypatch.setattr(monitor, "xbmc", SimpleNamespace(
        Monitor=lambda: SimpleNamespace(waitForAbort=lambda _: player.advance() or False),
        getCondVisibility=player.condition,
    ))
    reporter = Reporter(player)
    monitor.watch(STREAM, reporter)
    return reporter


def test_reports_start_heartbeats_and_stop(monkeypatch):
    reports = watch(monkeypatch, ScriptedPlayer(range(1, 2 * PLAYHEAD_INTERVAL + 2))).reports
    last = 2 * PLAYHEAD_INTERVAL + 1
    assert reports == [1, PLAYHEAD_INTERVAL + 1, last, last]


def test_pausing_reports_nothing_and_the_heartbeat_comes_after_45_s_anyway(monkeypatch):
    positions = [1, 2, 3] + [3] * 50 + [4, 5]
    reports = watch(monkeypatch, ScriptedPlayer(positions, paused=range(3, 53))).reports
    assert reports == [1, 4, 5], "the first tick played after the pause is 45 s past the start"


def test_a_seek_is_reported_once_playback_goes_on(monkeypatch):
    player = ScriptedPlayer([1, 2, 600, 600, 601, 602], seeks={2}, caching={2, 3})
    reporter = watch(monkeypatch, player)
    assert reporter.reports == [1, 601, 602]
    assert reporter.loaded == 2


def test_a_seek_while_paused_reports_nothing(monkeypatch):
    reports = watch(monkeypatch, ScriptedPlayer([1, 2, 600, 601], paused={1, 2}, seeks={2})).reports
    assert reports == [1, 601], "the last report is the stop"


def test_a_rebuffering_is_reported_once_playback_goes_on(monkeypatch):
    reports = watch(monkeypatch, ScriptedPlayer([1, 2, 3, 3, 4, 5], caching={3})).reports
    assert reports == [1, 4, 5]


def test_first_report_waits_for_the_real_position_and_that_wait_is_loading(monkeypatch):
    reporter = watch(monkeypatch, ScriptedPlayer([0, 0, 315, 316, 317]))
    assert reporter.reports[0] == 315
    assert reporter.loaded == 1.0, "two half-second waits"


def test_stops_when_kodi_moves_to_the_next_episode(monkeypatch):
    reports = watch(monkeypatch, ScriptedPlayer(list(range(1, 31)) + list(range(1, 300)), switch_at=30)).reports
    assert reports[-1] == 30, reports[-1]  # never the next episode's position


def test_the_next_video_resolved_while_this_one_plays_ends_its_following(monkeypatch):
    player = ScriptedPlayer(range(1, 100), next_resolved_at=20)
    reporter = watch(monkeypatch, player)
    assert (reporter.reports[-1], player.tick) == (20, 20), "its last position, while Kodi still plays it"
    assert "plugin.video.adn.watching" not in HomeWindow.properties, "the next video may go on"


def test_next_video_waits_until_the_previous_one_sent_its_last_report(monkeypatch):
    HomeWindow.properties = {"plugin.video.adn.watching": STREAM}
    waits = []

    def wait(seconds):
        waits.append(seconds)
        if len(waits) == 3:
            HomeWindow.properties.pop("plugin.video.adn.watching")  # its last report is done
        return False

    monkeypatch.setattr(monitor.xbmcgui, "Window", HomeWindow)
    monkeypatch.setattr(monitor, "xbmc", SimpleNamespace(Monitor=lambda: SimpleNamespace(waitForAbort=wait)))
    monitor.wait_for_previous()
    assert len(waits) == 3
    assert HomeWindow.properties == {"plugin.video.adn.handover": "1"}, "the previous one was told to stop"


def test_seek_callback_flags_a_report_and_gives_the_seek_target():
    player = monitor._EventPlayer()
    assert (player.seeked, player.seek_position) == (False, None)
    player.onPlayBackSeek(600500, 30000)  # milliseconds, as Kodi passes them
    assert (player.seeked, player.seek_position) == (True, 600)
