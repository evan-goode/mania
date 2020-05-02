from abc import ABC, abstractmethod
from collections import namedtuple
from enum import Enum
from typing import Callable, List, NamedTuple, Optional, Tuple, Type, Union


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


class Client(ABC):
    @abstractmethod
    def authenticate(self):
        pass

    @abstractmethod
    def search(
        self, query: str, media_type: Type[Union[Track, Album, Artist]], count: int
    ):
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
