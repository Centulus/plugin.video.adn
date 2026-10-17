"""User-facing strings, in the menu language chosen in the add-on settings.

Read straight from the bundled ``strings.po`` rather than through Kodi, so the
menus can be French while Kodi is in English. English fills any gap.
To add a language: translate its strings.po, list it in ``_FOLDERS`` and in
the ``ui_language`` options of settings.xml.
"""
from __future__ import annotations

import functools
import os
import re

import xbmcaddon

_FOLDERS = {"fr": "fr_fr", "en": "en_gb"}
_DEFAULT = "fr"
_FALLBACK = "en_gb"
_LANGUAGE_DIR = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "language")
_PO_ENTRY = re.compile(r'msgctxt "#(\d+)"\s*\nmsgid "(?:[^"\\]|\\.)*"\s*\nmsgstr "((?:[^"\\]|\\.)*)"')


class L:
    RESUME = 30100
    MY_LIST = 30101
    FOR_YOU = 30102
    SEARCH = 30103
    CATALOGUE = 30104
    CHANGE_PROFILE = 30105
    RECOMMENDED = 30106
    BECAUSE_YOU_WATCHED = 30107
    SIGN_OUT = 30109
    LOGIN_FAILED = 30120
    CODE_SENT_TO = 30121
    SIGNED_OUT = 30123
    ADD_TO_LIST = 30124
    REMOVE_FROM_LIST = 30125
    ADDED_TO_LIST = 30126
    REMOVED_FROM_LIST = 30127
    PROFILE_SELECTED = 30128
    SIGN_IN = 30130
    USERNAME_PROMPT = 30131
    PASSWORD_PROMPT = 30132
    WRONG_CREDENTIALS = 30133
    WRONG_CODE = 30134
    SIGNED_IN_AS = 30135
    GO_TO_SERIES = 30136
    GO_TO_SEASON = 30137
    WHO_IS_WATCHING = 30138
    CONFIRM_SIGN_OUT = 30139
    ENTER_CODE = 30140
    CURRENT_PROFILE = 30141
    SIGN_OUT_HINT = 30142
    SIGN_IN_HINT = 30143
    NO_STREAM = 30144
    RESUMES_AT = 30145


def tr(string_id: int) -> str:
    text = _strings(_folder()).get(string_id) or _strings(_FALLBACK).get(string_id)
    assert text, string_id
    return text


@functools.lru_cache(maxsize=None)
def _folder() -> str:
    return _FOLDERS.get(xbmcaddon.Addon().getSetting("ui_language"), _FOLDERS[_DEFAULT])


@functools.lru_cache(maxsize=None)
def _strings(folder: str) -> dict:
    path = os.path.join(_LANGUAGE_DIR, f"resource.language.{folder}", "strings.po")
    with open(path, encoding="utf-8") as po:
        entries = _PO_ENTRY.findall(po.read())
    return {int(string_id): text.replace('\\"', '"') for string_id, text in entries}
