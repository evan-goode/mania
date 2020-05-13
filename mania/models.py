from abc import ABC, abstractmethod
from collections import namedtuple
from enum import Enum
from typing import Callable, List, NamedTuple, Optional, Tuple, Type, Union


class ManiaException(Exception):
    exit_code = 0


class ManiaSeriousException(ManiaException):
    exit_code = 1


class UnavailableException(Exception):
    pass


class Artist(NamedTuple):
    id: str
    name: str


class Album(NamedTuple):
    id: str
    name: str
    artists: List[Artist]
    year: Optional[str]
    cover_url: Optional[str]


class Track(NamedTuple):
    id: str
    name: str
    artists: List[Artist]
    album: Album
    track_number: int
    disc_number: int
    quality: str
    extension: str


Media = Union[Track, Album, Artist]
MediaType = Union[Type[Track], Type[Album], Type[Artist]]


class Client(ABC):
    @abstractmethod
    def authenticate(self):
        pass

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
    def get_media(self, track: Track) -> Tuple[str, Optional[Callable[[str], None]]]:
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
