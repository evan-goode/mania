from abc import ABC, abstractmethod

class Media(ABC):
    def __init__(self, **media):
        self.provider = media["provider"]
        self.id = media["id"]

class Song(Media):
    def __init__(self, **song):
        super().__init__(**song)
        self.name = song["name"]
        self.extension = song["extension"]
        self.track_number = song["track_number"]
        self.disc_number = song["disc_number"]
        self.album = song["album"]
        self.artist = song["artist"]

class Album(Media):
    def __init__(self, **album):
        super().__init__(**album)
        self.name = album["name"]
        self.cover_art_url = album["cover_art_url"]
        self.year = album["year"]
        self.artist = album["artist"]

class Artist(Media):
    def __init__(self, **artist):
        super().__init__(**artist)
        self.name = artist["name"]

class Client(ABC):
    @abstractmethod
    def search(self, query, media_type, count):
        pass
    @abstractmethod
    def get_album_songs(self, album):
        pass
    @abstractmethod
    def get_artist_albums(self, artist):
        pass
    @abstractmethod
    def get_media_url(self, song):
        pass
