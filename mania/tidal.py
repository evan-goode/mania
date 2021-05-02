"""Tidal authentication and API client"""

from operator import itemgetter
from typing import cast, Any, Callable, Dict, List, Optional, Tuple, Type, Union
from urllib.parse import urlparse
import base64
import datetime
import json
import locale
import re
import sys
import time

import requests

from .models import Track, Album, Artist, Media, MediaType, Client, UnavailableException

LOCALE = locale.getlocale()[0]

# API_SCHEME_AND_DOMAIN = "https://api.tidalhifi.com"
API_ENDPOINT = "https://api.tidalhifi.com/v1"
AUTH_ENDPOINT = "https://auth.tidal.com/v1"
CLIENT_ID = "aR7gUaTK1ihpXOEP"
CLIENT_SECRET = "eVWBEkuL2FCjxgjOkR3yK0RYZEbcrMXRc2l8fU3ZCdE="
DEVICE_TYPE = "TABLET"
USER_AGENT = "TIDAL_ANDROID/1000 okhttp/3.10.0"
CLIENT_VERSION = "2.26.1"
MAXIMUM_LIMIT = 50

SPECIAL_AUDIO_MODES = frozenset(("DOLBY_ATMOS", "SONY_360RA"))
COVER_ART_SIZE = 1280
MAXIMUM_ATTEMPTS = 4


class TidalAuthError(Exception):
    """Error authenticating to TIDAL"""


class TidalSession:
    """Adapted from
    https://github.com/Dniel97/RedSea/blob/master/redsea/sessions.py. Thanks,
    Daniel!"""

    def __init__(
        self,
        device_code: Optional[str] = None,
        user_code: Optional[str] = None,
        country_code: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        user_id: Optional[str] = None,
        expires: Optional[datetime.datetime] = None,
    ):
        self.device_code = device_code
        self.user_code = user_code
        self.country_code = country_code
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.user_id = user_id
        self.expires = expires
        self._session = requests.Session()

    def to_dict(self) -> Dict[str, Any]:
        """Get the session parameters as a dict, for serialization"""
        return {
            "device_code": self.device_code,
            "user_code": self.user_code,
            "country_code": self.country_code,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "user_id": self.user_id,
            "expires": self.expires,
        }

    def check_valid(self) -> None:
        """Raise a TidalAuthError if session is invalid"""
        if self.access_token is None:
            raise TidalAuthError("Missing access token.")

        if self.expires is not None and datetime.datetime.now() > self.expires:
            self._refresh()
        subscription_response = self.request(
            "GET", f"users/{self.user_id}/subscription"
        )
        try:
            subscription_response.raise_for_status()
            assert subscription_response.json()["subscription"]["type"] == "HIFI"
        except requests.exceptions.HTTPError as error:
            raise TidalAuthError("Session is invalid.") from error
        except AssertionError as error:
            raise TidalAuthError("You need a HiFi subscription.") from error

    def authenticate(self) -> None:
        """Authenticate as a new linked device"""
        # retrieve csrf token for subsequent request
        authorization_response = self._session.post(
            f"{AUTH_ENDPOINT}/oauth2/device_authorization",
            data={
                "client_id": CLIENT_ID,
                "scope": "r_usr w_usr",
            },
        )

        if authorization_response.status_code == 400:
            raise TidalAuthError(
                "Authorization failed! Is the clientid/token up to date?"
            )
        try:
            authorization_response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            raise TidalAuthError("Authorization failed!") from error

        authorization_json = authorization_response.json()
        self.device_code = authorization_json["deviceCode"]
        self.user_code = authorization_json["userCode"]
        print(
            "Go to https://link.tidal.com/{} and log in or sign up to TIDAL.".format(
                self.user_code
            )
        )

        data = {
            "client_id": CLIENT_ID,
            "device_code": self.device_code,
            "client_secret": CLIENT_SECRET,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "scope": "r_usr w_usr",
        }

        status_code = 400
        print("Checking link", end="")

        while status_code == 400:
            last_index = 1
            for index, char in enumerate("." * 5, start=1):
                sys.stdout.write(char)
                sys.stdout.flush()
                # exchange access code for oauth token
                time.sleep(0.2)
                last_index = index
            token_response = requests.post(f"{AUTH_ENDPOINT}/oauth2/token", data=data)
            status_code = token_response.status_code

            # backtrack the written characters, overwrite them with space,
            # backtrack again:
            sys.stdout.write("\b" * last_index + " " * last_index + "\b" * last_index)
            sys.stdout.flush()

        print("." * 5)

        try:
            token_response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            raise TidalAuthError(
                "Auth Error: " + token_response.json().get("error")
            ) from error

        print("Successfully linked!")

        token_json = token_response.json()

        self.access_token = token_json["access_token"]
        self.refresh_token = token_json["refresh_token"]
        self.expires = datetime.datetime.now() + datetime.timedelta(
            seconds=token_json["expires_in"]
        )

        sessions_response = requests.get(
            "https://api.tidal.com/v1/sessions",
            headers=self._auth_headers(),
        )
        sessions_response.raise_for_status()
        sessions_json = sessions_response.json()
        self.user_id = sessions_json["userId"]
        self.country_code = sessions_json["countryCode"]

        self.check_valid()

    def _refresh(self) -> None:
        if self.refresh_token is None:
            raise TidalAuthError("Refresh token is missing.")
        refresh_response = requests.post(
            f"{AUTH_ENDPOINT}/oauth2/token",
            data={
                "refresh_token": self.refresh_token,
                "client_id": CLIENT_ID,
                "grant_type": "refresh_token",
            },
        )
        try:
            refresh_response.raise_for_status()
        except requests.response.HTTPError as error:
            raise TidalAuthError("Error refreshing token!") from error
        refresh_json = refresh_response.json()

        self.access_token = refresh_json["access_token"]
        self.expires = datetime.datetime.now() + datetime.timedelta(
            seconds=refresh_json["expires_in"]
        )

    def _auth_headers(self) -> Dict[str, str]:
        return {
            "Host": "api.tidal.com",
            "X-Tidal-Token": CLIENT_ID,
            "Authorization": f"Bearer {self.access_token}",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "User-Agent": "TIDAL_ANDROID/1000 okhttp/3.13.1",
        }

    def request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        attempt: int = 1,
    ) -> requests.models.Response:
        """Make a request to TIDAL API"""

        assert self.country_code is not None

        full_params = {**(params or {}), "countryCode": self.country_code}
        url = f"{API_ENDPOINT}/{path}"

        try:
            response = self._session.request(
                method, url, params=full_params, data=data, headers=self._auth_headers()
            )
            # response = self._session.request(
            #     method,
            #     url,
            #     params=params,
            #     data=data,
            #     headers=self._auth_headers(),
            #     proxies={"https": "https://localhost:8000"},
            #     verify="mitmproxy-ca-cert.pem",
            # )
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            status = error.response.status_code
            if (
                status == 429
                or (status == 500 and error.response.json().get("subStatus") == 999)
            ) and attempt < MAXIMUM_ATTEMPTS:
                # backoff and retry if we receive a 429 Client Error: Too Many Requests for url
                time.sleep(2 ** attempt)
                return self.request(
                    method,
                    path,
                    params,
                    data,
                    attempt=attempt + 1,
                )
            if status in (401, 403):
                # refresh session and retry
                self._refresh()
                return self.request(
                    method, path, params, data, attempt=MAXIMUM_ATTEMPTS
                )
            raise error

        return response


class TidalClient(Client):
    """TIDAL API Client"""

    def __init__(self, config: dict, tidal_session: TidalSession):
        self._tidal_session = tidal_session
        self._search_count = config["search-count"]
        self._quality = config["quality"]

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
    def _get_cover_url(cover: str) -> str:
        return f"https://resources.tidal.com/images/{cover.replace('-', '/')}/{COVER_ART_SIZE}x{COVER_ART_SIZE}.jpg"

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
    ) -> requests.models.Response:
        return self._tidal_session.request(method, path, params, data)

    def _paginate(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
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
            response = self._request(method, path, params, data).json()
            items += response["items"]
            if len(items) >= response["totalNumberOfItems"]:
                break
            params["offset"] += params["limit"]
        return items

    def _get_quality(self, tidal_object: dict) -> Tuple[str, str]:
        quality_levels = {"low": 1, "high": 2, "lossless": 3, "master": 4}

        special_audio_modes = (
            frozenset(tidal_object.get("audioModes", ())) & SPECIAL_AUDIO_MODES
        )

        if tidal_object["audioQuality"] == "LOSSLESS" or special_audio_modes:
            available_qualities = frozenset(("lossless", "high", "low"))
            best_available = "lossless"
        elif tidal_object["audioQuality"] == "HI_RES":
            available_qualities = frozenset(("master", "lossless", "high", "low"))
            best_available = "master"
        elif tidal_object["audioQuality"] == "HIGH":
            available_qualities = frozenset(("high", "low"))
            best_available = "high"
        elif tidal_object["audioQuality"] == "LOW":
            available_qualities = frozenset(("low",))
            best_available = "low"

        # get highest quality available, limited by self._quality preference
        desired_level = quality_levels[self._quality]
        chosen_quality = max(
            (
                quality
                for quality, level in quality_levels.items()
                if level <= desired_level and quality in available_qualities
            ),
            key=quality_levels.get,
        )

        return chosen_quality, best_available

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

        _, best_available_quality = self._get_quality(tidal_album)

        return Album(
            id=tidal_album["id"],
            name=tidal_album["title"],
            artists=artists,
            year=year,
            cover_url=cover_url,
            best_available_quality=best_available_quality,
            explicit=tidal_album.get("explicit", False),
        )

    def _tidal_track_to_track(
        self, tidal_track: dict, album: Optional[Album] = None
    ) -> Track:
        # we can be pretty sure that an album ID is valid if it comes from TIDAL
        album = album or cast(Album, self.get_album_by_id(tidal_track["album"]["id"]))

        artists = [
            self._tidal_artist_to_artist(tidal_artist)
            for tidal_artist in tidal_track["artists"]
        ]

        chosen_quality, best_available_quality = self._get_quality(tidal_track)

        file_extension = {
            "master": "flac",
            "lossless": "flac",
            "high": "mp4",
            "low": "mp4",
        }[chosen_quality]

        return Track(
            id=tidal_track["id"],
            name=tidal_track["title"],
            artists=artists,
            album=album,
            explicit=tidal_track.get("explicit", False),
            track_number=tidal_track["trackNumber"],
            disc_number=tidal_track["volumeNumber"],
            chosen_quality=chosen_quality,
            best_available_quality=best_available_quality,
            file_extension=file_extension,
        )

    def search(
        self,
        query: str,
        media_type: Type[Union[Track, Album, Artist]],
        count: int,
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
        }[track.chosen_quality]

        try:
            playback_response = self._request(
                "GET",
                f"tracks/{track.id}/playbackinfopostpaywall",
                params={
                    "audioquality": tidal_quality,
                    "playbackmode": "STREAM",
                    "assetpresentation": "FULL",
                },
            )

            playback_response.raise_for_status()

            manifest = json.loads(
                base64.b64decode(playback_response.json()["manifest"])
            )
            return manifest["urls"][0]
        except requests.exceptions.HTTPError as error:
            status_code = error.response.status_code
            sub_status = error.response.json().get("subStatus")
            if (status_code, sub_status) == (401, 4005):
                raise UnavailableException() from error
            raise error

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
                "pages/data/2fbf68c2-dc58-49b1-b1be-6958e66383f3",
                params={
                    "albumId": album.id,
                },
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
            params={
                "artistId": artist.id,
            },
        )
        return [self._tidal_album_to_album(tidal_album) for tidal_album in tidal_albums]
