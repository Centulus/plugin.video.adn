"""Sign-in, profile, sign-out and My list actions."""
from __future__ import annotations

from ..adn.errors import AuthError, LoginCancelled, NotAuthenticated, TwoFactorRequired
from ..context import Context
from ..kodi import dialogs, listitems
from ..kodi.i18n import L, tr


def ensure_auth(ctx: Context) -> None:
    try:
        ctx.auth.ensure_authenticated()
    except NotAuthenticated:
        sign_in(ctx)


def sign_in(ctx: Context) -> None:
    """Email, password, then the 2FA code if needed; LoginCancelled on back."""
    username = ctx.settings.username
    while True:
        username = dialogs.ask_text(tr(L.USERNAME_PROMPT), username)
        password = dialogs.ask_password(tr(L.PASSWORD_PROMPT)) if username else ""
        if not password:
            raise LoginCancelled("login dialog closed")
        try:
            ctx.auth.login(username, password)
        except TwoFactorRequired as challenge:
            _enter_code(ctx, challenge)
        except AuthError:
            if dialogs.confirm(tr(L.WRONG_CREDENTIALS)):
                continue
            raise LoginCancelled("credentials refused") from None
        break
    dialogs.notify(tr(L.SIGNED_IN_AS) % username)
    _pick_profile(ctx, after_login=True)


def _enter_code(ctx: Context, challenge: TwoFactorRequired) -> None:
    heading = tr(L.CODE_SENT_TO) % challenge.destination if challenge.destination else tr(L.ENTER_CODE)
    while True:
        code = dialogs.ask_number(heading)
        if not code:
            raise LoginCancelled("code dialog closed")
        try:
            ctx.auth.verify_two_factor(challenge.token, code)
            return
        except AuthError:
            if not dialogs.confirm(tr(L.WRONG_CODE)):
                raise LoginCancelled("code refused") from None


def _pick_profile(ctx: Context, after_login: bool = False) -> None:
    """Ask which profile watches; right after login only when there is a choice."""
    profiles = ctx.api.profiles()
    if not profiles:
        return
    settings = ctx.settings
    if after_login and len(profiles) == 1:
        chosen = profiles[0]
    else:
        chosen = dialogs.choose_profile(tr(L.WHO_IS_WATCHING), profiles, settings.profile_id)
    if chosen is None and after_login:
        chosen = next((p for p in profiles if p.is_main), profiles[0])
    if chosen is None:
        return
    settings.profile_id = chosen.id
    settings.profile_name = chosen.name
    settings.age_category = chosen.age_category
    if not after_login:
        dialogs.notify(tr(L.PROFILE_SELECTED) % chosen.name)


def login(ctx: Context) -> None:
    sign_in(ctx)
    listitems.refresh()


def change_profile(ctx: Context) -> None:
    ensure_auth(ctx)
    _pick_profile(ctx)
    listitems.refresh()


def logout(ctx: Context) -> None:
    if dialogs.confirm(tr(L.CONFIRM_SIGN_OUT)):
        ctx.auth.logout()
        dialogs.notify(tr(L.SIGNED_OUT))
        listitems.refresh()


def watchlist_add(ctx: Context, show_id) -> None:
    ensure_auth(ctx)
    ctx.api.add_to_watchlist(int(show_id))
    dialogs.notify(tr(L.ADDED_TO_LIST))
    listitems.refresh()


def watchlist_remove(ctx: Context, show_id) -> None:
    ensure_auth(ctx)
    ctx.api.remove_from_watchlist(int(show_id))
    dialogs.notify(tr(L.REMOVED_FROM_LIST))
    listitems.refresh()
