from resources.lib.routing import Router

ROUTER = Router("plugin://plugin.video.adn/", 1)


def test_url_for_builds_the_exact_url_without_none_params():
    url = ROUTER.url_for("episodes", show_id=269, season=None)
    assert url == "plugin://plugin.video.adn/?action=episodes&show_id=269", url


def test_parse_reads_back_what_url_for_built():
    url = ROUTER.url_for("play", video_id=3629, show_id=269, season="1")
    assert Router.parse(url.split("?", 1)[1]) == ("play", {"video_id": "3629", "show_id": "269", "season": "1"})


def test_parse_defaults_to_root():
    assert Router.parse("") == ("root", {})
