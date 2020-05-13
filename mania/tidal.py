import base64
from functools import partial
import locale
import getpass
from operator import itemgetter
import random
import re
from string import ascii_lowercase
import time
from typing import cast, Any, Callable, List, Optional, Tuple, Type, Union
from urllib.parse import urlparse

from bidict import bidict
from Crypto.Cipher import AES
from Crypto.Util import Counter
import requests

from .models import Track, Album, Artist, Media, MediaType, Client, UnavailableException

LOCALE = locale.getlocale()[0]

# API_SCHEME_AND_DOMAIN = "https://api.tidalhifi.com"
API_ENDPOINT = "https://api.tidalhifi.com/v1"
API_TOKEN = "pl4Vc0hemlAXD0mN"
MASTER_API_TOKEN = "u5qPNNYIbD0S0o36MrAiFZ56K6qMCrCmYPzZuTnV"
USER_AGENT = "TIDAL_ANDROID/879 okhttp/3.10.0"
CLIENT_VERSION = "1.9.1"
DEVICE_TYPE = "TABLET"
MAXIMUM_LIMIT = 50
CLIENT_UNIQUE_KEY_LENGTH = 21
MASTER_KEY = "UIlTTEMmmLfGowo/UC60x2H45W6MdGgTRfo/umg4754="
SPECIAL_AUDIO_MODES = frozenset(("DOLBY_ATMOS", "SONY_360RA"))
COVER_ART_SIZE = 1280
MAXIMUM_ATTEMPTS = 4


class TidalClient(Client):
    def __init__(self, config: dict) -> None:
        self._search_count = config["search-count"]
        self._quality = config["quality"]

        self._username = config["username"] or input("Tidal username: ")
        self._password = config["password"] or getpass.getpass("Tidal password: ")

    def authenticate(self):
        self._session, self._country_code = TidalClient._get_session(
            self._username, self._password, API_TOKEN
        )
        self._master_session, _ = TidalClient._get_session(
            self._username, self._password, MASTER_API_TOKEN
        )

    def resolve_url(self, url: str) -> Tuple[MediaType, Optional[Media]]:
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        # find the last occurrence of "track", "album", or "artist" in the URL
        # path and assume that's the media type of the URL
        strings = {
            Track: "track",
            Album: "album",
            Artist: "artist",
        }
        indices = {
            media_type: path.rfind(string) for media_type, string in strings.items()
        }
        media_type, last_index = max(indices.items(), key=itemgetter(1))

        # if there were no matches
        if last_index == -1:
            raise ValueError(
                'Couldn\'t parse that URL. Try one like "https://tidal.com/browse/track/140538043".'
            )

        media_id = path.split("/")[-1]

        if not re.match(r"^\d+$", media_id):
            raise ValueError(
                'That URL doesn\'t end in an ID. Try one like "https://tidal.com/browse/track/140538043".'
            )

        handlers = {
            Track: self.get_track_by_id,
            Album: self.get_album_by_id,
            Artist: self.get_artist_by_id,
        }

        return media_type, handlers[media_type](media_id)

    @staticmethod
    def _get_session(
        username: str, password: str, token: str
    ) -> Tuple[requests.Session, str]:
        session = requests.Session()
        session.headers["User-Agent"] = USER_AGENT

        client_unique_key = "".join(
            random.choice(ascii_lowercase) for _ in range(CLIENT_UNIQUE_KEY_LENGTH)
        )

        request = session.post(
            f"{API_ENDPOINT}/login/username",
            data=TidalClient._prepare_params(
                {
                    "username": username,
                    "password": password,
                    "token": token,
                    "clientUniqueKey": client_unique_key,
                    "clientVersion": CLIENT_VERSION,
                }
            ),
        )
        request.raise_for_status()
        body = request.json()
        session.headers["x-tidal-sessionid"] = body["sessionId"]
        country_code = body["countryCode"]

        return session, country_code

    @staticmethod
    def _prepare_params(params: dict) -> dict:
        return {str.encode(key): str.encode(value) for key, value in params.items()}

    @staticmethod
    def _get_cover_url(cover: str) -> str:
        return f"https://resources.tidal.com/images/{cover.replace('-', '/')}/{COVER_ART_SIZE}x{COVER_ART_SIZE}.jpg"

    @staticmethod
    def _decrypt_security_token(security_token: bytes) -> Tuple[bytes, bytes]:
        # from https://github.com/yaronzz/Tidal-Media-Downloader/blob/master/TIDALDL-PY/tidal_dl/decryption.py, who took it from RedSea

        # decode the base64 strings to ascii strings
        master_key = base64.b64decode(MASTER_KEY)
        security_token = base64.b64decode(security_token)

        # get the IV from the first 16 bytes of the securityToken
        iv = security_token[:16]
        encrypted_st = security_token[16:]

        # initialize decryptor
        decryptor = AES.new(master_key, AES.MODE_CBC, iv)

        # decrypt the security token
        decrypted_st = decryptor.decrypt(encrypted_st)

        # get the audio stream decryption key and nonce from the decrypted security token
        key = decrypted_st[:16]
        nonce = decrypted_st[16:24]

        return key, nonce

    @staticmethod
    def _decrypt(key: bytes, nonce: bytes, path: str) -> None:
        counter = Counter.new(64, prefix=nonce, initial_value=0)
        decryptor = AES.new(key, AES.MODE_CTR, counter=counter)

        with open(path, "rb") as encrypted_file:
            decrypted = decryptor.decrypt(
                encrypted_file.read()
            )  # should probably do this in chunks
        with open(path, "wb") as decrypted_file:
            decrypted_file.write(decrypted)

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        use_master_session: bool = False,
        attempt: int = 1,
    ) -> requests.models.Response:

        full_params = {**(params or {}), "countryCode": self._country_code}
        url = f"{API_ENDPOINT}/{path}"

        session = self._master_session if use_master_session else self._session

        try:
            response = session.request(method, url, params=full_params, data=data)
            # request = session.request(
            #     method,
            #     url,
            #     params=params,
            #     data=data,
            #     proxies={"https": "https://localhost:8000"},
            #     verify="mitmproxy-ca-cert.pem",
            # )
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            if error.response.status_code == 429 and attempt < MAXIMUM_ATTEMPTS:
                # re-authenticate and retry if we receive a 429 Client Error: Too Many Requests for url
                time.sleep(2 ** attempt)
                self.authenticate()
                return self._request(
                    method,
                    path,
                    params,
                    data,
                    use_master_session=use_master_session,
                    attempt=attempt + 1,
                )
            raise error

        return response

    def _paginate(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        use_master_session: bool = False,
    ) -> List[Any]:
        items = []
        params = {
            "offset": 0,
            "limit": MAXIMUM_LIMIT,
            "deviceType": DEVICE_TYPE,
            "locale": LOCALE,
            **(params or {}),
        }
        while True:
            response = self._request(
                method, path, params, data, use_master_session=use_master_session
            ).json()
            items += response["items"]
            if len(items) >= response["totalNumberOfItems"]:
                break
            params["offset"] += params["limit"]
        return items

    def _tidal_artist_to_artist(self, tidal_artist: dict) -> Artist:
        return Artist(id=tidal_artist["id"], name=tidal_artist["name"])

    def _tidal_album_to_album(self, tidal_album: dict) -> Album:
        year: Optional[str]
        if tidal_album.get("releaseDate"):
            year = tidal_album["releaseDate"].split("-")[0]
        else:
            year = None

        cover_url: Optional[str]
        if tidal_album.get("cover"):
            cover_url = TidalClient._get_cover_url(tidal_album["cover"])
        else:
            cover_url = None

        artists = [
            self._tidal_artist_to_artist(tidal_artist)
            for tidal_artist in tidal_album["artists"]
        ]

        return Album(
            id=tidal_album["id"],
            name=tidal_album["title"],
            artists=artists,
            year=year,
            cover_url=cover_url,
        )

    def _get_quality_extension(self, tidal_track: dict) -> Tuple[str, str]:
        quality_levels = bidict({"low": 1, "high": 2, "lossless": 3, "master": 4})

        special_audio_modes = (
            frozenset(tidal_track.get("audioModes", ())) & SPECIAL_AUDIO_MODES
        )

        if tidal_track["audioQuality"] == "LOSSLESS" or special_audio_modes:
            available_qualities = frozenset(("lossless", "high", "low"))
        elif tidal_track["audioQuality"] == "HI_RES":
            available_qualities = frozenset(("master", "lossless", "high", "low"))
        elif tidal_track["audioQuality"] == "HIGH":
            available_qualities = frozenset(("high", "low"))
        elif tidal_track["audioQuality"] == "LOW":
            available_qualities = frozenset(("low",))

        # get highest quality available, limited by self._quality preference
        desired_level = quality_levels[self._quality]
        level = max(
            level
            for quality, level in quality_levels.items()
            if level <= desired_level and quality in available_qualities
        )
        quality = quality_levels.inverse[level]

        extension = {
            "master": "flac",
            "lossless": "flac",
            "high": "mp4",
            "low": "mp4",
        }[quality]

        return quality, extension

    def _tidal_track_to_track(
        self, tidal_track: dict, album: Optional[Album] = None
    ) -> Track:
        # we can be pretty sure that an album ID is valid if it comes from TIDAL
        album = album or cast(Album, self.get_album_by_id(tidal_track["album"]["id"]))

        artists = [
            self._tidal_artist_to_artist(tidal_artist)
            for tidal_artist in tidal_track["artists"]
        ]

        quality, extension = self._get_quality_extension(tidal_track)
        return Track(
            id=tidal_track["id"],
            name=tidal_track["title"],
            artists=artists,
            album=album,
            track_number=tidal_track["trackNumber"],
            disc_number=tidal_track["volumeNumber"],
            quality=quality,
            extension=extension,
        )

    def search(
        self, query: str, media_type: Type[Union[Track, Album, Artist]], count: int,
    ) -> List[Union[Track, Album, Artist]]:
        types, key, resolver = {
            Track: ("TRACKS", "tracks", self._tidal_track_to_track),
            Album: ("ALBUMS", "albums", self._tidal_album_to_album),
            Artist: ("ARTISTS", "artists", self._tidal_artist_to_artist),
        }[media_type]
        results = self._request(
            "GET",
            "search",
            params={
                "query": query,
                "types": types,
                "limit": min(self._search_count, MAXIMUM_LIMIT),
            },
        ).json()[key]["items"]
        return [resolver(result) for result in results]

    def get_media(self, track: Track) -> Tuple[str, Optional[Callable[[str], None]]]:
        tidal_quality = {
            "master": "HI_RES",
            "lossless": "LOSSLESS",
            "high": "HIGH",
            "low": "LOW",
        }[track.quality]

        decryptor: Optional[Callable[[str], None]]

        try:
            if tidal_quality == "HI_RES":
                response = self._request(
                    "GET",
                    f"tracks/{track.id}/streamUrl",
                    params={"soundQuality": tidal_quality,},
                    use_master_session=True,
                ).json()

                url = response["url"]
                key, nonce = TidalClient._decrypt_security_token(
                    response["encryptionKey"]
                )
                decryptor = partial(TidalClient._decrypt, key, nonce)
            else:
                response = self._request(
                    "GET",
                    f"tracks/{track.id}/urlpostpaywall",
                    params={
                        "urlusagemode": "OFFLINE",
                        "assetpresentation": "FULL",
                        "prefetch": "false",
                        "audioquality": tidal_quality,
                    },
                ).json()

                url = response["urls"][0]
                decryptor = None
        except requests.exceptions.HTTPError as error:
            status_code = error.response.status_code
            sub_status = error.response.json().get("subStatus")
            if (status_code, sub_status) == (401, 4005):
                raise UnavailableException()

        return url, decryptor

    def get_track_by_id(self, track_id: str) -> Optional[Track]:
        try:
            tidal_track = self._request("GET", f"tracks/{track_id}").json()
        except requests.HTTPError as error:
            if error.response.status_code == 404:
                return None
        return self._tidal_track_to_track(tidal_track)

    def get_album_by_id(self, album_id: str) -> Optional[Album]:
        try:
            tidal_album = self._request("GET", f"albums/{album_id}").json()
        except requests.HTTPError as error:
            if error.response.status_code == 404:
                return None
        return self._tidal_album_to_album(tidal_album)

    def get_artist_by_id(self, artist_id: str) -> Optional[Artist]:
        try:
            tidal_artist = self._request("GET", f"artists/{artist_id}").json()
        except requests.HTTPError as error:
            if error.response.status_code == 404:
                return None
        return self._tidal_artist_to_artist(tidal_artist)

    def get_album_tracks(self, album: Album) -> List[Track]:
        tidal_tracks = [
            element["item"]
            for element in self._paginate(
                "GET",
                f"pages/data/2fbf68c2-dc58-49b1-b1be-6958e66383f3",
                params={"albumId": album.id,},
            )
            if element["type"] == "track"
        ]
        return [
            self._tidal_track_to_track(tidal_track, album=album)
            for tidal_track in tidal_tracks
        ]

    def get_artist_albums(self, artist: Artist) -> List[Album]:
        tidal_albums = self._paginate(
            "GET",
            "pages/data/4b37c74b-f994-45dd-8fca-b7da2694da83",
            params={"artistId": artist.id,},
        )
        return [self._tidal_album_to_album(tidal_album) for tidal_album in tidal_albums]
