import pytest

from resources.lib.adn.errors import AdnHttpError
from resources.lib.player.playhead import PlayheadReporter


class RecordingApi:
    """Refuses the access tokens listed in ``expired``."""

    def __init__(self, expired=()):
        self.reports = []
        self.expired = set(expired)

    def report_progress(self, _, body, access_token):
        if access_token in self.expired:
            raise AdnHttpError(401, "/viewing/history/video/1")
        self.reports.append((access_token, body))


class Session:
    guid = "GUID"
    access_token = "A1"

    def __init__(self, viewtime=95):
        self.viewtime = viewtime
        self.reports = 0

    def reported(self):
        self.reports += 1

    def token(self, _):
        self.access_token = "A2"


def reporter(api, session=None, duration=1440):
    return PlayheadReporter(api, session or Session(), 3628, duration, "vostf", "auto")


def test_report_carries_session_guid_and_what_is_played_in_order():
    api = RecordingApi()
    reporter(api).report(120)
    assert api.reports == [("A1", {
        "guid": "GUID", "viewtime": 95, "stoptime": 120, "duration": 1440,
        "language": "vostf", "quality": "auto", "source": "AndroidTV",
    })]
    assert list(api.reports[0][1]) == ["guid", "viewtime", "stoptime", "duration", "language", "quality", "source"]


@pytest.mark.parametrize("position, viewtime", [(0, 95), (120, 0), (1500, 95)])
def test_nothing_is_sent_at_zero_or_past_the_end(position, viewtime):
    api, session = RecordingApi(), Session(viewtime)
    reporter(api, session).report(position)
    assert (api.reports, session.reports) == ([], 0), "and the heartbeat clock is not reset"


def test_one_second_past_the_end_is_the_end():
    api = RecordingApi()
    reporter(api).report(1441)
    assert api.reports[0][1]["stoptime"] == 1440


@pytest.mark.parametrize("played, sent", [(0, 1440), (1442, 1442), (1438, 1440), (1300, 1300)])
def test_duration_is_the_players_when_it_differs_by_more_than_2_s(played, sent):
    api = RecordingApi()
    reporter(api).report(100, played)
    assert api.reports[0][1]["duration"] == sent


def test_an_expired_access_token_gets_a_new_player_token_and_the_report_resent():
    api = RecordingApi(expired={"A1"})
    reporter(api).report(200)
    assert [(token, body["stoptime"]) for token, body in api.reports] == [("A2", 200)]


def test_failed_report_never_raises():
    class Down:
        def report_progress(self, *_):
            raise ConnectionError("offline")

    reporter(Down()).report(10)
