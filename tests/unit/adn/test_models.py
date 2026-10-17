from resources.lib.adn.models import Profile, Rail, Season, Show, Streams, Video, resume_point


def test_show_prefers_hidpi_art_and_reads_genres():
    show = Show.from_json(
        {
            "id": 1046,
            "title": "Berserk",
            "type": "EPS",
            "genres": ["Action", "Seinen"],
            "image": "a.jpg",
            "image2x": "a@2x.jpg",
            "imageHorizontal2x": "h@2x.jpg",
            "episodeCount": 25,
        }
    )
    assert show.poster == "a@2x.jpg", show.poster
    assert show.thumb == "h@2x.jpg", show.thumb
    assert show.genres == ("Action", "Seinen"), show.genres
    assert show.is_movie is False


def test_movie_kind_detected():
    assert Show.from_json({"id": 1, "title": "x", "type": "MOV"}).is_movie is True


def test_video_reads_resume_and_parent_show():
    video = Video.from_json(
        {
            "id": 3628,
            "title": "Fairy Tail - Épisode 1",
            "number": "Épisode 1",
            "shortNumber": "1",
            "season": "1",
            "duration": 1377,
            "user": {"stoptime": 93, "isFullyWatched": False},
            "show": {"id": 269},
        }
    )
    assert video.stoptime == 93, video.stoptime
    assert video.fully_watched is False
    assert video.show_id == 269, video.show_id
    assert video.season == "1", video.season


def test_season_and_rail():
    assert Season.from_json({"season": "2", "title": "Saison 2"}).number == "2"
    rail = Rail.from_json({"title": "Populaire", "elements": [{"id": 1, "title": "x", "type": "EPS"}]})
    assert rail.title == "Populaire"
    assert len(rail.shows) == 1


def test_profile_reads_age_category_and_main_flag():
    profile = Profile.from_json(
        {"id": 1, "name": "centulus", "ageCategory": 18, "main": True, "avatar": "a.jpg"}
    )
    assert profile.id == 1
    assert profile.age_category == 18, profile.age_category
    assert profile.is_main is True


def test_streams_reads_title_duration_tracks_and_subtitles():
    streams = Streams.from_json(
        {
            "links": {"streaming": {"vostf": {"auto": "u"}}, "subtitles": {"vostf": "s"}},
            "video": {"duration": 1439, "currentTime": 315},
            "metadata": {"title": "Charlotte - Épisode 3"},
        }
    )
    assert (streams.title, streams.duration, streams.resume_at) == ("Charlotte - Épisode 3", 1439, 315)
    assert streams.pick("vostf", "auto") == ("vostf", "auto", "u")
    assert streams.subtitles == {"vostf": "s"}


def test_streams_pick_reports_what_it_falls_back_to():
    streams = Streams(by_language={"vostf": {"sd": "s", "auto": "a"}})
    assert streams.pick("vostf", "sd") == ("vostf", "sd", "s")
    assert streams.pick("vostf", "fhd") == ("vostf", "auto", "a"), "missing quality falls back to auto"
    assert streams.pick("vf", "sd") == ("vostf", "sd", "s"), "missing track falls back to the first one"


def test_resume_at_uses_adn_position_mid_episode():
    video = Video.from_json({"id": 1, "duration": 1440, "user": {"stoptime": 315}})
    assert video.resume_at == 315, video.resume_at


def test_a_video_starts_over_past_90_percent_only():
    assert [resume_point(position, 1440) for position in (0, 1296, 1297, 1440, 1500)] == [0, 1296, 0, 0, 0]
    assert resume_point(315, 0) == 0, "no duration, no resume"
