"""The play action."""
from __future__ import annotations

from functools import partial

from ..adn.errors import AdnError, NotAuthenticated
from ..context import Context
from ..kodi import dialogs
from ..kodi.i18n import L, tr
from ..player import playback, season_queue
from . import entries
from .account import ensure_auth, sign_in


def play(ctx: Context, video_id, show_id="0", season="") -> None:
    with playback.failing_resolve(ctx.router.handle):
        ensure_auth(ctx)
    try:
        playback.play(ctx, int(video_id), int(show_id), season, partial(entries.season_entry, ctx))
    except NotAuthenticated:  # Kodi already knows this play failed: sign in, the user plays again
        sign_in(ctx)
    except AdnError as exc:
        dialogs.log(f"playback of video {video_id} failed: {exc}")
        if not season_queue.is_active():  # inside a queued season, Kodi just skips ahead
            dialogs.notify(tr(L.NO_STREAM))
