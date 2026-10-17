"""List entries shared by the routes: URLs, context menus, shows and videos."""
from __future__ import annotations

from ..adn.models import Video
from ..context import Context
from ..kodi import listitems
from ..kodi.i18n import L, tr


def series_url(ctx: Context, show_id) -> str:
    return ctx.router.url_for("series", show_id=show_id)


def season_url(ctx: Context, show_id, season) -> str:
    return ctx.router.url_for("episodes", show_id=show_id, season=season)


def play_url(ctx: Context, video: Video) -> str:
    # Listings and the season playlist must use the same URL per video.
    return ctx.router.url_for("play", video_id=video.id, show_id=video.show_id, season=video.season)


def my_list(ctx: Context) -> set:
    """Show ids in My list; empty when signed out."""
    return ctx.api.watchlist_show_ids() if ctx.auth.is_logged_in else set()


def resume_hint(video: Video) -> str:
    return tr(L.RESUMES_AT) % listitems.clock(video.resume_at) if video.resume_at else ""


def show_items(ctx: Context, shows) -> list:
    listed = my_list(ctx)
    return [
        listitems.show_item(show, series_url(ctx, show.id), _watchlist_menu(ctx, show.id, listed))
        for show in shows
    ]


def video_items(ctx: Context, videos, *, mixed: bool, listed: set) -> list:
    """Playable entries; ``mixed`` lists hold several shows and link to each."""
    season_counts = ctx.api.season_counts(v.show_id for v in videos if not v.is_movie) if mixed else {}
    return [
        listitems.video_item(
            video,
            play_url(ctx, video),
            mixed=mixed,
            resume_hint=resume_hint(video),
            context_menu=(_navigation_menu(ctx, video, season_counts) if mixed else [])
            + _watchlist_menu(ctx, video.show_id, listed),
        )
        for video in videos
    ]


def season_entry(ctx: Context, video: Video, item=None) -> tuple:
    """A row of the season playlist, labelled as on the season page."""
    return listitems.video_item(video, play_url(ctx, video), mixed=False, resume_hint=resume_hint(video), item=item)


def _watchlist_menu(ctx: Context, show_id, listed: set) -> list:
    if not ctx.auth.is_logged_in or not show_id:
        return []
    if show_id in listed:
        url = ctx.router.url_for("watchlist_remove", show_id=show_id)
        return [(tr(L.REMOVE_FROM_LIST), listitems.run_action(url))]
    url = ctx.router.url_for("watchlist_add", show_id=show_id)
    return [(tr(L.ADD_TO_LIST), listitems.run_action(url))]


def _navigation_menu(ctx: Context, video: Video, season_counts: dict) -> list:
    """"Go to series", plus "Go to season" when the show has several."""
    if video.is_movie or not video.show_id:
        return []
    menu = [(tr(L.GO_TO_SERIES), listitems.open_listing(series_url(ctx, video.show_id)))]
    if video.season and season_counts.get(video.show_id, 1) > 1:
        menu.append((tr(L.GO_TO_SEASON), listitems.open_listing(season_url(ctx, video.show_id, video.season))))
    return menu
