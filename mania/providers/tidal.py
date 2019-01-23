import locale
import getpass
import requests
# from hyper.contrib import HTTP20Adapter

from .. import models

[LOCALE, _] = locale.getlocale()

# API_SCHEME_AND_DOMAIN = "https://api.tidalhifi.com"
API_ENDPOINT = "https://api.tidalhifi.com/v1"
API_TOKEN = "pl4Vc0hemlAXD0mN"
USER_AGENT = "TIDAL_ANDROID/879 okhttp/3.10.0"
CLIENT_VERSION = "2.10.1"
DEVICE_TYPE = "TABLET"
MAXIMUM_LIMIT = 50
CLIENT_UNIQUE_KEY = "kjadsfjkhsadkjhasdkjh" # apparently, this string is arbitrary:
# https://github.com/lucaslg26/TidalAPI/issues/22

COVER_ART_SIZE = 1280

class TidalClient(models.Client):
    name = "TIDAL"
    def __init__(self, config):
        username = config["tidal-username"] or input("Tidal username: ")
        password = config["tidal-password"] or getpass.getpass("Tidal password: ")
        self._search_count = config["search-count"]
        self._quality = config["tidal-quality"]
        self._session = requests.Session()
        # self._session.mount(API_SCHEME_AND_DOMAIN, HTTP20Adapter())
        self._session.headers["user-agent"] = USER_AGENT
        request = self._session.post(f"{API_ENDPOINT}/login/username", data=self._prepare_params({
            "username": username,
            "password": password,
            "token": API_TOKEN,
            "clientUniqueKey": CLIENT_UNIQUE_KEY,
            "clientVersion": CLIENT_VERSION,
        }))
        request.raise_for_status()
        body = request.json()
        self._session.headers["x-tidal-sessionid"] = body["sessionId"]
        self._country_code = body["countryCode"]
    @staticmethod
    def _prepare_params(params):
        return {
            str.encode(key): str.encode(value) for key, value in params.items()
        }
    @staticmethod
    def _get_cover_art_url(cover):
        return f"https://resources.tidal.com/images/{cover.replace('-', '/')}/{COVER_ART_SIZE}x{COVER_ART_SIZE}.jpg"
    def _request(self, method, path, params=None, data=None):
        params = {**{
            "countryCode": self._country_code,
        }, **(params or {})}
        url = f"{API_ENDPOINT}/{path}"
        request = self._session.request(method, url, params=params, data=data)
        # request = self._session.request(method, url, params=params, data=data, proxies={"https": "localhost:8080"}, verify="mitmproxy-ca-cert.pem")
        request.raise_for_status()
        return request
    def _paginate(self, method, path, params=None, data=None):
        items = []
        params = {**{
            "offset": 0,
            "limit": MAXIMUM_LIMIT,
            "deviceType": DEVICE_TYPE,
            "locale": LOCALE,
        }, **(params or {})}
        while True:
            response = self._request(method, path, params, data).json()
            items += response["items"]
            if len(items) >= response["totalNumberOfItems"]:
                break
            params["offset"] += params["limit"]
        return items
    def tidal_artist_to_artist(self, tidal_artist):
        return models.Artist(
            provider=self,
            id=tidal_artist["id"],
            name=tidal_artist["name"],
        )
    def tidal_album_to_album(self, tidal_album):
        year = tidal_album["releaseDate"].split("-")[0]
        print(tidal_album["cover"])
        cover_art_url = self._get_cover_art_url(tidal_album["cover"]) if tidal_album["cover"] else None
        if cover_art_url is None:
            print(tidal_album)
        artists = [self.tidal_artist_to_artist(tidal_artist) for tidal_artist in tidal_album["artists"]]
        return models.Album(
            provider=self,
            id=tidal_album["id"],
            name=tidal_album["title"],
            artists=artists,
            year=year,
            cover_art_url=cover_art_url,
        )
    def tidal_song_to_song(self, tidal_song, album=None):
        album = album or self.get_album(tidal_song["album"]["id"])
        artists = [self.tidal_artist_to_artist(tidal_artist) for tidal_artist in tidal_song["artists"]]
        return models.Song(
            provider=self,
            id=tidal_song["id"],
            name=tidal_song["title"],
            artists=artists,
            album=album,
            track_number=tidal_song["trackNumber"],
            disc_number=tidal_song["volumeNumber"],
            extension=("flac"
                       if self._quality == "lossless" and tidal_song["audioQuality"] in ["LOSSLESS", "HI_RES"]
                       else "mp4"),
        )
    def search(self, query, media_type, count):
        types, key, resolver = {
            models.Song: ("TRACKS", "tracks", self.tidal_song_to_song),
            models.Album: ("ALBUMS", "albums", self.tidal_album_to_album),
            models.Artist: ("ARTISTS", "artists", self.tidal_artist_to_artist),
        }[media_type]
        results = self._request("GET", "search", params={
            "query": query,
            "types": types,
            "limit": min(self._search_count, MAXIMUM_LIMIT),
        }).json()[key]["items"]
        return [resolver(result) for result in results]
    def get_media_url(self, song):
        response = self._request("GET", f"tracks/{song.id}/urlpostpaywall", params={
            "urlusagemode": "OFFLINE",
            "assetpresentation": "FULL",
            "prefetch": "false",
            "audioquality": {
                "lossless": "LOSSLESS",
                "high": "HIGH",
                "low": "LOW",
            }[self._quality],
        }).json()
        return response["urls"][0]
    def get_album(self, album_id):
        album = self._request("GET", f"albums/{album_id}").json()
        return self.tidal_album_to_album(album)
    def get_album_songs(self, album):
        songs = [element["item"] for element in self._paginate("GET", f"pages/data/2fbf68c2-dc58-49b1-b1be-6958e66383f3", params={
            "albumId": album.id,
        })]
        return [self.tidal_song_to_song(song, album=album) for song in songs]
    def get_artist_albums(self, artist):
        albums = self._paginate("GET", "pages/data/4b37c74b-f994-45dd-8fca-b7da2694da83", params={
            "artistId": artist.id,
        })
        return [self.tidal_album_to_album(album) for album in albums]
