"""Abstract base classes. Unfortuntaely, these are mostly useless indirections
since TIDAL is now the only supported back-end."""

from abc import ABC, abstractmethod
from typing import Callable, List, NamedTuple, Optional, Tuple, Type, Union


class ManiaException(Exception):
    """Base exception class for setting an exit code"""

    exit_code = 0


class ManiaSeriousException(ManiaException):
    """A serious exception with a non-zero exit code"""

    exit_code = 1


class UnavailableException(Exception):
    """For region-locked or otherwise unavailable items"""


class Artist(NamedTuple):
    """A musical artist"""

    id: str
    name: str


class Album(NamedTuple):
    """An album with one or more artists"""

    id: str
    name: str
    artists: List[Artist]
    year: Optional[str]
    explicit: bool
    cover_url: Optional[str]
    best_available_quality: str


class Track(NamedTuple):
    """A track with an album and one or more artists"""

    id: str
    name: str
    artists: List[Artist]
    album: Album
    explicit: bool
    track_number: int
    disc_number: int
    chosen_quality: str
    best_available_quality: str
    file_extension: str


Media = Union[Track, Album, Artist]
MediaType = Union[Type[Track], Type[Album], Type[Artist]]


class Client(ABC):
    """An abstract streaming service client"""

    @abstractmethod
    def search(self, query: str, media_type: MediaType, count: int):
        pass

    @abstractmethod
    def get_album_tracks(self, album: Album) -> List[Track]:
        pass

    @abstractmethod
    def get_artist_albums(self, artist: Artist) -> List[Album]:
        pass

    @abstractmethod
    def get_media(self, track: Track) -> str:
        pass

    @abstractmethod
    def get_artist_by_id(self, artist_id: str):
        pass

    @abstractmethod
    def get_album_by_id(self, album_id: str):
        pass

    @abstractmethod
    def get_track_by_id(self, track_id: str):
        pass

    @abstractmethod
    def resolve_url(self, url: str) -> Tuple[MediaType, Optional[Media]]:
        pass
