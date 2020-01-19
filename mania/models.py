from abc import ABC, abstractmethod


class ManiaException(Exception):
    exit_code = 2

    def __init__(self, message, config):
        super().__init__(message)
        self.config = config


class ManiaSeriousException(ManiaException):
    exit_code = 1

    def __init__(self, message, config):
        super().__init__(message)
        self.config = config


class Media(ABC):
    def __init__(self, **media):
        self.provider = media["provider"]
        self.id = media["id"]


class Artifact(Media):
    def __init__(self, **artifact):
        super().__init__(**artifact)
        self.artists = artifact["artists"]

    def get_primary_artist_name(self, config):
        if len(self.artists) > 1 and config["various-artists"]:
            return "Various Artists"
        return self.artists[0].name


class Song(Artifact):
    def __init__(self, **song):
        super().__init__(**song)
        self.name = song["name"]
        self.extension = song["extension"]
        self.track_number = song["track_number"]
        self.disc_number = song["disc_number"]
        self.album = song["album"]


class Album(Artifact):
    def __init__(self, **album):
        super().__init__(**album)
        self.cover_art_url = album.get("cover_art_url")
        self.name = album["name"]
        self.year = album["year"]


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
