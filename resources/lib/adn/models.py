"""Typed views over the ADN API payloads."""
from __future__ import annotations

from dataclasses import dataclass, field

from .constants import WATCHED_SHARE, Quality


def resume_point(position: int, duration: int) -> int:
    """Where a video left at ``position`` starts: there, or over once 90 % is seen."""
    return 0 if position >= duration or position > duration * WATCHED_SHARE else position


@dataclass
class Show:
    """A series or a movie."""

    id: int
    title: str
    kind: str = "EPS"  # "EPS" or "MOV"
    summary: str = ""
    genres: tuple = ()
    year: str = ""
    studio: str = ""
    poster: str = ""
    thumb: str = ""
    logo: str = ""
    carousel: str = ""

    @classmethod
    def from_json(cls, data: dict) -> Show:
        return cls(
            id=data.get("id") or 0,
            title=data.get("title") or "",
            kind=data.get("type") or "EPS",
            summary=data.get("summary") or "",
            genres=tuple(data.get("genres") or ()),
            year=data.get("firstReleaseYear") or "",
            studio=data.get("productionStudio") or "",
            poster=data.get("image2x") or data.get("image") or "",
            thumb=data.get("imageHorizontal2x") or data.get("imageHorizontal") or "",
            logo=data.get("logo") or "",
            carousel=data.get("carouselLandscape") or "",
        )

    @property
    def is_movie(self) -> bool:
        return self.kind == "MOV"


@dataclass
class Video:
    """An episode or a movie, with its show and the viewer's progress."""

    id: int
    show: Show
    title: str = ""         # "Charlotte - Épisode 2"
    name: str = ""          # episode title
    number: str = ""        # "Épisode 2", "Film"
    short_number: str = ""  # "2"
    season: str = ""        # "1", "" when the show has no seasons
    kind: str = "EPS"
    summary: str = ""
    duration: int = 0
    thumb: str = ""
    stoptime: int = 0
    fully_watched: bool = False

    @classmethod
    def from_json(cls, data: dict) -> Video:
        user = data.get("user") or {}
        return cls(
            id=data["id"],
            show=Show.from_json(data.get("show") or {}),
            title=data.get("title") or "",
            name=data.get("name") or "",
            number=data.get("number") or "",
            short_number=data.get("shortNumber") or "",
            season=data.get("season") or "",
            kind=data.get("type") or "EPS",
            summary=data.get("summary") or "",
            duration=data.get("duration") or 0,
            thumb=data.get("image2x") or data.get("image") or "",
            stoptime=user.get("stoptime") or 0,
            fully_watched=bool(user.get("isFullyWatched")),
        )

    @property
    def show_id(self) -> int:
        return self.show.id

    @property
    def is_movie(self) -> bool:
        return self.kind == "MOV"

    @property
    def resume_at(self) -> int:
        return resume_point(self.stoptime, self.duration)


@dataclass
class Profile:
    id: int
    name: str
    avatar: str = ""
    age_category: int = 18
    is_main: bool = False

    @classmethod
    def from_json(cls, data: dict) -> Profile:
        return cls(
            id=data["id"],
            name=data.get("name") or "",
            avatar=data.get("avatar") or "",
            age_category=data.get("ageCategory") or 18,
            is_main=bool(data.get("main")),
        )


@dataclass
class Season:
    number: str
    title: str

    @classmethod
    def from_json(cls, data: dict) -> Season:
        return cls(number=data.get("season") or "", title=data.get("title") or "")


@dataclass
class Rail:
    """A titled row of the home page."""

    title: str
    shows: tuple = ()

    @classmethod
    def from_json(cls, data: dict) -> Rail:
        return cls(
            title=data.get("title") or "",
            shows=tuple(Show.from_json(show) for show in data.get("elements") or ()),
        )


@dataclass
class Streams:
    """The stream link of one video: m3u8 URLs per track and quality, subtitles."""

    title: str = ""
    duration: int = 0
    current_time: int = 0  # ADN's saved position
    by_language: dict = field(default_factory=dict)  # {"vostf": {"auto": url, ...}}
    subtitles: dict = field(default_factory=dict)    # {"vostf": url}

    @classmethod
    def from_json(cls, data: dict) -> Streams:
        links = data.get("links") or {}
        return cls(
            title=(data.get("metadata") or {}).get("title") or "",
            duration=(data.get("video") or {}).get("duration") or 0,
            current_time=(data.get("video") or {}).get("currentTime") or 0,
            by_language=links.get("streaming") or {},
            subtitles=links.get("subtitles") or {},
        )

    @property
    def resume_at(self) -> int:
        return resume_point(self.current_time, self.duration)

    def pick(self, language: str, quality: str) -> tuple:
        """``(language, quality, url)`` of the wanted stream, else the closest available."""
        if language not in self.by_language:
            language = next(iter(self.by_language), language)
        qualities = self.by_language.get(language) or {}
        if quality not in qualities:
            quality = Quality.AUTO if Quality.AUTO in qualities else next(iter(qualities), quality)
        return language, quality, qualities.get(quality, "")
