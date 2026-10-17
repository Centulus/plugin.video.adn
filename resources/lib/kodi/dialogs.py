"""Dialogs, notifications and the add-on log."""
from __future__ import annotations

import xbmc
import xbmcgui

from ..adn.models import Profile


def log(message: str, level: int = xbmc.LOGWARNING) -> None:
    xbmc.log(f"[plugin.video.adn] {message}", level)


def notify(message: str) -> None:
    xbmcgui.Dialog().notification("ADN", message, xbmcgui.NOTIFICATION_INFO, 3000)


def ask_text(heading: str, default: str = "") -> str:
    """Typed text, "" when the user backs out (same for the other prompts)."""
    return xbmcgui.Dialog().input(heading, defaultt=default, type=xbmcgui.INPUT_ALPHANUM)


def ask_password(heading: str) -> str:
    return xbmcgui.Dialog().input(heading, type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)


def ask_number(heading: str) -> str:
    return xbmcgui.Dialog().input(heading, type=xbmcgui.INPUT_NUMERIC)


def confirm(message: str) -> bool:
    return xbmcgui.Dialog().yesno("ADN", message)


def choose_profile(heading: str, profiles: list, current_id: str) -> Profile | None:
    entries = []
    for profile in profiles:
        entry = xbmcgui.ListItem(label=profile.name)
        entry.setArt({"icon": profile.avatar, "thumb": profile.avatar})
        entries.append(entry)
    current = next((i for i, profile in enumerate(profiles) if str(profile.id) == current_id), -1)
    index = xbmcgui.Dialog().select(heading, entries, preselect=current, useDetails=True)
    return profiles[index] if index >= 0 else None
