"""Context menus of the playable entries."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from resources.lib.adn.models import Video
from resources.lib.kodi import listitems
from resources.lib.kodi.i18n import L, tr
from resources.lib.routes import entries
from resources.lib.routing import Router


def episode(video_id, show_id, season="1", kind="EPS"):
    return Video.from_json({"id": video_id, "season": season, "type": kind, "show": {"id": show_id}})


@pytest.fixture
def menus_of(monkeypatch):
    menus = []
    monkeypatch.setattr(
        listitems, "video_item",
        lambda _, url, **kw: menus.append([label for label, _ in kw["context_menu"]]) or (url, None, False),
    )

    def build(videos, season_counts, listed, mixed=True):
        api = MagicMock()
        api.season_counts.side_effect = lambda _: season_counts
        ctx = SimpleNamespace(router=Router("plugin://x/", 1), api=api, auth=SimpleNamespace(is_logged_in=True))
        entries.video_items(ctx, videos, mixed=mixed, listed=set(listed))
        return menus

    return build


def test_one_season_show_offers_series_only(menus_of):
    assert menus_of([episode(1, 1425)], {1425: 1}, []) == [[tr(L.GO_TO_SERIES), tr(L.ADD_TO_LIST)]]


def test_several_seasons_offer_series_and_season(menus_of):
    menus = menus_of([episode(1, 269)], {269: 9}, [])
    assert menus == [[tr(L.GO_TO_SERIES), tr(L.GO_TO_SEASON), tr(L.ADD_TO_LIST)]], menus


def test_show_already_in_my_list_offers_removal(menus_of):
    assert menus_of([episode(1, 269)], {269: 1}, [269]) == [[tr(L.GO_TO_SERIES), tr(L.REMOVE_FROM_LIST)]]


def test_movie_has_no_navigation_shortcut(menus_of):
    assert menus_of([episode(1, 851, season="", kind="MOV")], {}, []) == [[tr(L.ADD_TO_LIST)]]


def test_season_page_has_no_navigation_shortcut(menus_of):
    assert menus_of([episode(1, 269)], {}, [], mixed=False) == [[tr(L.ADD_TO_LIST)]]
