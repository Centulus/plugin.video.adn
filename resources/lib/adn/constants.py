"""Values tied to ADN, sent verbatim."""
from __future__ import annotations

BASE_URL = "https://gw.api.animationdigitalnetwork.com"

SOURCE = "AndroidTV"
SUBTITLE_KEY_SUFFIX = "bd48b5e0ae1b97cc"  # depends on SOURCE

COMMON_HEADERS = {
    "x-source": SOURCE,
    "accept-language": "fr",
    "origin": "adn-android",
    "accept-encoding": "gzip",
    "user-agent": "okhttp/4.12.0",
    "cookie": "aws-waf-token=no valid token",
}

HOME_LAYOUT = "PS4"
STREAM_LINK_PARAMS = {
    "source": SOURCE,
    "withMetadata": "true",
    "subtitlesFormat": "webvtt",
    "freeWithAds": "false",
    "adaptive": "true",
}
ALL = -1
RECOMMENDED_LIMIT = 10
HISTORY_LIMIT = 20
WATCHLIST_LIMIT = 100

PLAYHEAD_INTERVAL = 45
WATCHED_SHARE = 0.9
SAME_DURATION = 2


class Language:
    SUB = "vostf"
    DUB = "vf"
    DEFAULT = SUB


class Quality:
    AUTO = "auto"
    DEFAULT = AUTO
