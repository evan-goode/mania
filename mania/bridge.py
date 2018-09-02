from abc import ABC, abstractmethod
import itertools

import getpass
from gmusicapi import Mobileclient as GoogleMobileClient
from . import tidal as tidalapi

class Media(ABC):
    def __init__(self, **media):
        self.provider = media["provider"]
        self.id = media.get("id", None)
        self.name = media["name"]

class Song(Media):
    def __init__(self, **song):
        super().__init__(**song)
        self.year = song.get("year", None)
        self.extension = song.get("extension", None)
        self.track_number = song["track_number"]
        self.disc_number = song["disc_number"]
        self.album = song["album"]
        self.artist = song["artist"]

class Album(Media):
    def __init__(self, **album):
        super().__init__(**album)
        self.cover_art_url = album["cover_art_url"]
        self.year = album.get("year", None)
        self.artist = album["artist"]

class Artist(Media):
    def __init__(self, **artist):
        super().__init__(**artist)

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

class GoogleClient(Client):
    name = "Google Play Music"
    def __init__(self, config):
        self.quality = {
            "high": "hi",
            "medium": "med",
            "low": "low",
        }[config["google-quality"]]
        username = config["google-username"] or input("Google username: ")
        password = config["google-password"] or getpass.getpass("Google password: ")
        android_id = config["google-android-id"] or GoogleMobileClient.FROM_MAC_ADDRESS
        self.client = GoogleMobileClient(debug_logging=config["debug-logging"])
        logged_in = self.client.login(
            username,
            password,
            android_id,
        )
        if not logged_in:
            raise Exception("Google authentication failed.")
    def google_song_to_song(self, google_song):
        cover_art_url = (google_song["albumArtRef"][0]["url"]
                         if google_song["albumArtRef"]
                         else None)
        return Song(
            provider=self,
            id=google_song["storeId"],
            name=google_song["title"],
            year=google_song["year"],
            track_number=google_song["trackNumber"],
            disc_number=google_song["discNumber"],
            extension="mp3",
            artist=Artist(
                provider=self,
                id=google_song["artistId"],
                name=google_song["artist"],
            ),
            album=Album(
                provider=self,
                id=google_song["albumId"],
                name=google_song["album"],
                cover_art_url=cover_art_url,
                artist=Artist(
                    provider=self,
                    # we don't know the ID of the album artist
                    name=google_song["albumArtist"],
                ),
            ),
        )
    def google_album_to_album(self, google_album):
        return Album(
            provider=self,
            id=google_album["albumId"],
            name=google_album["name"],
            year=str(google_album["year"]),
            cover_art_url=google_album["albumArtRef"],
            artist=Artist(
                provider=self,
                id=google_album["artistId"][0] if google_album["artistId"] else None,
                name=google_album["artist"]
            )
        )

    def google_artist_to_artist(self, google_artist):
        return Artist(
            provider=self,
            id=google_artist["artistId"],
            name=google_artist["name"],
        )

    def get_album_songs(self, album):
        google_songs = self.client.get_album_info(album.id, include_tracks=True)["tracks"]
        return [self.google_song_to_song(google_song) for google_song in google_songs]

    def get_artist_albums(self, artist):
        google_albums = self.client.get_artist_info(artist.id,
                                                    include_albums=True,
                                                    max_rel_artist=0,
                                                    max_top_tracks=0)["albums"]
        return [self.google_album_to_album(google_album) for google_album in google_albums]

    def search(self, query, media_type, count):
        if media_type is Song:
            results = self.client.search(query, count)["song_hits"][:count]
            return [self.google_song_to_song(google_song["track"]) for google_song in results]
        if media_type is Album:
            results = self.client.search(query, count)["album_hits"][:count]
            return [self.google_album_to_album(google_album["album"]) for google_album in results]
        if media_type is Artist:
            results = self.client.search(query, count)["artist_hits"][:count]
            return [self.google_artist_to_artist(google_artist["artist"])
                    for google_artist in results]
        raise Exception("unknown media_type")

    def get_media_url(self, song):
        return self.client.get_stream_url(song.id, quality=self.quality)

    def increment_play_count(self, song):
        self.client.increment_song_playcount(song.id)

class TidalClient(Client):
    name = "TIDAL"
    def __init__(self, config):
        username = config["tidal-username"] or input("Tidal username: ")
        password = config["tidal-password"] or getpass.getpass("Tidal password: ")
        self.quality = getattr(tidalapi.Quality, config["tidal-quality"])
        self.client = tidalapi.Session(tidalapi.Config(quality=self.quality))
        self.client.login(username, password)
    def tidal_song_to_song(self, tidal_song):
        return Song(
            provider=self,
            id=tidal_song.id,
            name=tidal_song.name,
            track_number=tidal_song.track_num,
            disc_number=tidal_song.disc_num,
            extension=("flac"
                       if self.quality is tidalapi.Quality.lossless
                       else "mp4"),
            artist=Artist(
                provider=self,
                id=tidal_song.artist.id,
                name=tidal_song.artist.name,
            ),
            album=Album(
                provider=self,
                id=tidal_song.album.id,
                name=tidal_song.album.name,
                cover_art_url=tidal_song.album.cover_art_url,
                artist=Artist(
                    provider=self,
                    name=tidal_song.album.artist.name,
                ),
            ),
        )
    def tidal_album_to_album(self, tidal_album):
        return Album(
            provider=self,
            id=tidal_album.id,
            name=tidal_album.name,
            year=tidal_album.release_date.strftime("%Y"),
            cover_art_url=tidal_album.cover_art_url,
            artist=Artist(
                provider=self,
                id=tidal_album.artist.id,
                name=tidal_album.artist.name,
            ),
        )
    def tidal_artist_to_artist(self, tidal_artist):
        return Artist(
            provider=self,
            id=tidal_artist.id,
            name=tidal_artist.name,
        )
    def search(self, query, media_type, count):
        if media_type is Song:
            results = self.client.search("track", query).tracks[:count]
            return [self.tidal_song_to_song(tidal_song) for tidal_song in results]
        if media_type is Album:
            results = self.client.search("album", query).albums[:count]
            return [self.tidal_album_to_album(tidal_album) for tidal_album in results]
        if media_type is Artist:
            results = self.client.search("artist", query).artists[:count]
            return [self.tidal_artist_to_artist(tidal_artist) for tidal_artist in results]
        raise Exception("unknown media_type")
    def get_media_url(self, song):
        return self.client.get_media_url(song.id)
    def get_album_songs(self, album):
        songs = self.client.get_album_tracks(album.id)
        return [self.tidal_song_to_song(song) for song in songs]
    def get_artist_albums(self, artist):
        albums = self.client.get_artist_albums(artist.id)
        return [self.tidal_album_to_album(album) for album in albums]

class Bridge(Client):
    def __init__(self, config):
        self.providers = []
        if config["tidal"]:
            self.providers.append(TidalClient(config))
        if config["google"]:
            self.providers.append(GoogleClient(config))
        if not self.providers:
            raise Exception("no providers!")
    def search(self, query, media_type, count):
        by_provider = [provider.search(query,
                                       media_type,
                                       count) for provider in self.providers]
        return list(itertools.chain.from_iterable(by_provider))
    def get_album_songs(self, album):
        return album.provider.get_album_songs(album)
    def get_artist_albums(self, artist):
        return artist.provider.get_artist_albums(artist)
    def get_media_url(self, song):
        return song.provider.get_media_url(song)
