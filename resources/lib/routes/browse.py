"""Listings: root menu, Resume, My list, For you, catalogue, search, series and seasons."""
from __future__ import annotations

from ..context import Context
from ..kodi import dialogs, listitems
from ..kodi.i18n import L, tr
from . import entries
from .account import ensure_auth

_ICON = {
    "history": "DefaultInProgressShows.png",
    "watchlist": "DefaultFavourites.png",
    "for_you": "DefaultRecentlyAddedEpisodes.png",
    "search": "DefaultAddonsSearch.png",
    "catalogue": "DefaultTVShows.png",
    "rail": "DefaultGenre.png",
    "profile": "DefaultUser.png",
    "account": "DefaultAddonService.png",
}


def root(ctx: Context) -> None:
    url = ctx.router.url_for
    items = [
        listitems.directory_item(tr(L.RESUME), url("history"), icon=_ICON["history"]),
        listitems.directory_item(tr(L.MY_LIST), url("watchlist"), icon=_ICON["watchlist"]),
        listitems.directory_item(tr(L.FOR_YOU), url("for_you"), icon=_ICON["for_you"]),
        listitems.directory_item(tr(L.SEARCH), url("search"), icon=_ICON["search"]),
        listitems.directory_item(tr(L.CATALOGUE), url("catalogue"), icon=_ICON["catalogue"]),
    ]
    if ctx.auth.is_logged_in:
        profile = ctx.settings.profile_name or ctx.settings.profile_id
        items.append(listitems.action_item(
            tr(L.CHANGE_PROFILE), url("change_profile"), icon=_ICON["profile"], plot=tr(L.CURRENT_PROFILE) % profile
        ))
        items.append(listitems.action_item(
            tr(L.SIGN_OUT), url("logout"), icon=_ICON["account"], plot=tr(L.SIGN_OUT_HINT)
        ))
    else:
        items.append(listitems.action_item(
            tr(L.SIGN_IN), url("login"), icon=_ICON["account"], plot=tr(L.SIGN_IN_HINT)
        ))
    listitems.end_directory(ctx.router.handle, items, content="files")


def history(ctx: Context) -> None:
    ensure_auth(ctx)
    items = entries.video_items(ctx, ctx.api.history(), mixed=True, listed=entries.my_list(ctx))
    listitems.end_directory(ctx.router.handle, items, content="episodes")


def watchlist(ctx: Context) -> None:
    ensure_auth(ctx)
    videos = ctx.api.watchlist()
    items = entries.video_items(ctx, videos, mixed=True, listed={video.show_id for video in videos})
    listitems.end_directory(ctx.router.handle, items, content="episodes")


def for_you(ctx: Context) -> None:
    url = ctx.router.url_for
    items = [
        listitems.directory_item(tr(L.RECOMMENDED), url("recommended"), icon=_ICON["for_you"]),
        listitems.directory_item(tr(L.BECAUSE_YOU_WATCHED), url("viewing_recommended"), icon=_ICON["for_you"]),
    ]
    listitems.end_directory(ctx.router.handle, items, content="files")


def recommended(ctx: Context) -> None:
    ensure_auth(ctx)
    _shows(ctx, ctx.api.recommended())


def viewing_recommended(ctx: Context) -> None:
    ensure_auth(ctx)
    _shows(ctx, ctx.api.viewing_recommended())


def catalogue(ctx: Context) -> None:
    items = [
        listitems.directory_item(rail.title, ctx.router.url_for("rail", title=rail.title), icon=_ICON["rail"])
        for rail in ctx.api.home()
        if rail.shows
    ]
    listitems.end_directory(ctx.router.handle, items, content="files")


def rail(ctx: Context, title) -> None:
    _shows(ctx, next((r.shows for r in ctx.api.home() if r.title == title), ()))


def search(ctx: Context) -> None:
    query = dialogs.ask_text(tr(L.SEARCH))
    _shows(ctx, ctx.api.search(query) if query else ())


def series(ctx: Context, show_id) -> None:
    seasons = ctx.api.seasons(int(show_id))
    if len(seasons) <= 1:
        return episodes(ctx, show_id)
    items = [
        listitems.directory_item(season.title, entries.season_url(ctx, show_id, season.number))
        for season in seasons
    ]
    listitems.end_directory(ctx.router.handle, items, content="seasons")


def episodes(ctx: Context, show_id, season="") -> None:
    videos = ctx.api.episodes(int(show_id), season)
    items = entries.video_items(ctx, videos, mixed=False, listed=entries.my_list(ctx))
    listitems.end_directory(ctx.router.handle, items, content="episodes")


def _shows(ctx: Context, shows) -> None:
    listitems.end_directory(ctx.router.handle, entries.show_items(ctx, shows), content="tvshows")
