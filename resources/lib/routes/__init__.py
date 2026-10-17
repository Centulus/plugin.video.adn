"""Plugin actions: each URL ``action`` maps to a ``handler(ctx, **params)``."""
from __future__ import annotations

import xbmcplugin

from ..adn.errors import AuthError, LoginCancelled, NotAuthenticated
from ..context import Context
from ..kodi import dialogs
from ..kodi.i18n import L, tr
from . import account, browse, play

HANDLERS = {
    "root": browse.root,
    "history": browse.history,
    "watchlist": browse.watchlist,
    "for_you": browse.for_you,
    "recommended": browse.recommended,
    "viewing_recommended": browse.viewing_recommended,
    "catalogue": browse.catalogue,
    "rail": browse.rail,
    "search": browse.search,
    "series": browse.series,
    "episodes": browse.episodes,
    "play": play.play,
    "login": account.login,
    "change_profile": account.change_profile,
    "logout": account.logout,
    "watchlist_add": account.watchlist_add,
    "watchlist_remove": account.watchlist_remove,
}


def run(ctx: Context) -> None:
    """Run the action of ``ctx.query``; a failed or cancelled login ends it quietly."""
    action, params = ctx.router.parse(ctx.query)
    handler = HANDLERS.get(action)
    assert handler is not None, ctx.query
    try:
        try:
            handler(ctx, **params)
        except NotAuthenticated:  # ADN refused the stored session
            account.sign_in(ctx)
            handler(ctx, **params)
    except LoginCancelled:
        _fail_listing(ctx)
    except AuthError as exc:
        dialogs.log(f"authentication failed: {exc}")
        dialogs.notify(tr(L.LOGIN_FAILED))
        _fail_listing(ctx)


def _fail_listing(ctx: Context) -> None:
    if ctx.router.handle >= 0:
        xbmcplugin.endOfDirectory(ctx.router.handle, succeeded=False)
