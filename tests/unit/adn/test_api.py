"""AdnApi requests: public calls without token, profile header elsewhere."""
from types import SimpleNamespace

from resources.lib.adn.api import AdnApi
from resources.lib.adn.errors import AdnHttpError
from resources.lib.adn.http import AdnHttpClient

from ..fakes import FakeResponse, FakeSession


def make(*responses):
    session = FakeSession(list(responses))
    client = AdnHttpClient(session)
    client.auth_headers = lambda: {"authorization": "Bearer T"}
    return AdnApi(client, SimpleNamespace(profile_id="7", age_category="16")), session


def test_home_and_search_are_public_calls():
    api, session = make(FakeResponse(200, {"home": []}), FakeResponse(200, {"shows": []}))
    api.home()
    api.search("frieren")
    for call in session.calls:
        assert "authorization" not in call["headers"], call["url"]
        assert "x-profile-id" not in call["headers"], call["url"]
    assert session.calls[1]["url"].endswith(
        "/show/catalog?search=frieren&limit=-1&genres=&maxAgeCategory=16"
    ), session.calls[1]["url"]


def test_episodes_carry_the_profile_and_the_season():
    api, session = make(FakeResponse(200, {"videos": [{"id": 1, "show": {"id": 269}}]}))
    videos = api.episodes(269, "2")
    call = session.calls[0]
    assert (call["headers"]["authorization"], call["headers"]["x-profile-id"]) == ("Bearer T", "7")
    assert call["url"].endswith("/video/show/269?offset=0&limit=-1&order=asc&season=2"), call["url"]
    assert [video.id for video in videos] == [1]


def test_stream_link_sends_the_player_token_first():
    api, session = make(FakeResponse(200, {"links": {}}))
    api.stream_link(3628, "PLAYER")
    assert list(session.calls[0]["headers"])[:2] == ["x-player-token", "x-source"]
    assert "authorization" not in session.calls[0]["headers"]


def test_progress_is_authenticated_by_the_player_access_token():
    api, session = make(FakeResponse(200, text=""))
    api.report_progress(3628, {"guid": "G"}, "ACCESS")
    names = list(session.calls[0]["headers"])
    assert names[3:5] == ["x-player-access-token", "x-profile-id"], names
    assert "authorization" not in names
    assert session.calls[0]["headers"]["x-player-access-token"] == "ACCESS"


def test_season_counts_treat_a_failed_show_as_one_season():
    api, _ = make()

    def seasons(show_id):
        if show_id == 269:
            return ["1", "2", "3"]
        raise AdnHttpError(500, f"/show/{show_id}/season")

    api.seasons = seasons
    assert api.season_counts([269, 1425, 269]) == {269: 3, 1425: 1}
