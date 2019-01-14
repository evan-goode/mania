import itertools

from . import models
from .providers.google import GoogleClient
from .providers.tidal import TidalClient

class NoProvidersException(Exception):
    pass

class Bridge(models.Client):
    def __init__(self, config):
        self._providers = []
        if config["tidal"]:
            self._providers.append(TidalClient(config))
        if config["google"]:
            self._providers.append(GoogleClient(config))
        if not self._providers:
            raise NoProvidersException(f"No streaming providers are set up. Configure and enable downloading from Google Play Music, TIDAL, or both in {config['config-file']}.")
    def search(self, query, media_type, count):
        by_provider = [provider.search(query,
                                       media_type,
                                       count) for provider in self._providers]
        return list(itertools.chain.from_iterable(by_provider))
    def get_album_songs(self, album):
        return album.provider.get_album_songs(album)
    def get_artist_albums(self, artist):
        return artist.provider.get_artist_albums(artist)
    def get_media_url(self, song):
        return song.provider.get_media_url(song)
