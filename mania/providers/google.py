import getpass
from gmusicapi import Mobileclient as GoogleMobileClient

from .. import models

class GoogleClient(models.Client):
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
    def google_song_to_song(self, google_song, album=None):
        cover_art_url = (google_song["albumArtRef"][0]["url"]
                         if google_song["albumArtRef"]
                         else None)
        return models.Song(
            provider=self,
            id=google_song["storeId"],
            name=google_song["title"],
            year=google_song["year"],
            track_number=google_song["trackNumber"],
            disc_number=google_song["discNumber"],
            extension="mp3",
            artist=models.Artist(
                provider=self,
                id=google_song["artistId"],
                name=google_song["artist"],
            ),
            album=album or models.Album(
                provider=self,
                id=google_song["albumId"],
                name=google_song["album"],
                cover_art_url=cover_art_url,
                artist=models.Artist(
                    provider=self,
                    # we don't know the ID of the album artist
                    name=google_song["albumArtist"],
                ),
            ),
        )
    def google_album_to_album(self, google_album, artist=None):
        return Album(
            provider=self,
            id=google_album["albumId"],
            name=google_album["name"],
            year=str(google_album["year"]),
            cover_art_url=google_album["albumArtRef"],
            artist=artist or models.Artist(
                provider=self,
                id=google_album["artistId"][0] if google_album["artistId"] else None,
                name=google_album["artist"]
            )
        )

    def google_artist_to_artist(self, google_artist):
        return models.Artist(
            provider=self,
            id=google_artist["artistId"],
            name=google_artist["name"],
        )

    def get_album_songs(self, album):
        google_songs = self.client.get_album_info(album.id, include_tracks=True)["tracks"]
        return [self.google_song_to_song(google_song, album=album) for google_song in google_songs]

    def get_artist_albums(self, artist):
        google_albums = self.client.get_artist_info(artist.id,
                                                    include_albums=True,
                                                    max_rel_artist=0,
                                                    max_top_tracks=0)["albums"]
        return [self.google_album_to_album(google_album, artist=artist) for google_album in google_albums]

    def search(self, query, media_type, count):
        if media_type is models.Song:
            results = self.client.search(query, count)["song_hits"][:count]
            return [self.google_song_to_song(google_song["track"]) for google_song in results]
        if media_type is models.Album:
            results = self.client.search(query, count)["album_hits"][:count]
            return [self.google_album_to_album(google_album["album"]) for google_album in results]
        if media_type is models.Artist:
            results = self.client.search(query, count)["artist_hits"][:count]
            return [self.google_artist_to_artist(google_artist["artist"])
                    for google_artist in results]
        raise Exception("unknown media_type")

    def get_media_url(self, song):
        return self.client.get_stream_url(song.id, quality=self.quality)

    def increment_play_count(self, song):
        self.client.increment_song_playcount(song.id)
