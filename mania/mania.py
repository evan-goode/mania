"""Main logic"""

import argparse
import os
import sys
from typing import cast, List, Optional
import traceback

import questionary
import requests
import toml
from tqdm import tqdm

from . import constants
from .models import (
    ManiaException,
    ManiaSeriousException,
    UnavailableException,
    Client,
    Track,
    Album,
    Artist,
    Media,
    MediaType,
)
from . import metadata
from .tidal import TidalAuthError, TidalSession, TidalClient


def log(config: dict, message: str = "", indent: int = 0) -> None:
    """Log a message to stdout unless config["quiet"] is set. Optionally indent
    by `indent` levels"""
    if message is not None and not config["quiet"]:
        print(constants.INDENT * indent + str(message))


def sanitize(config: dict, string: str, length_padding: int = 0) -> str:
    """Sanitize a string for use as a filesystem path"""
    if config["nice-format"]:
        alphanumeric = "".join(c for c in string if c.isalnum() or c in (" ", "-"))
        hyphenated = alphanumeric.replace(" ", "-")
        sanitized = "-".join(word for word in hyphenated.split("-") if word).lower()
    else:
        illegal_characters = frozenset("/")
        sanitized = "".join(c for c in string if c not in illegal_characters)

    # get maximum filename length (bytes)
    max_length = os.statvfs(config["output-directory"]).f_namemax

    # truncate unicode string to a byte count
    encoded = sanitized.encode("utf-8")[: max_length - length_padding]
    return encoded.decode("utf-8", "ignore")


def search(
    client: Client,
    config: dict,
    media_type: MediaType,
    query: str,
) -> Media:
    if config["by-id"]:
        result = {
            Track: client.get_track_by_id,
            Album: client.get_album_by_id,
            Artist: client.get_artist_by_id,
        }[media_type](query)
        if result is None:
            media_type_name = {
                Track: "track",
                Album: "album",
                Artist: "artist",
            }[media_type]
            raise ManiaSeriousException(
                f"Couldn't find the {media_type_name} with ID {query}."
            )
        return result

    log(config, "Searching...")
    results = client.search(query, media_type, config["search-count"])
    if not results:
        raise ManiaSeriousException("No results found.")
    if config["lucky"]:
        return results[0]

    def label_track(track: Track) -> str:
        name = track.name
        artists = ", ".join([artist.name for artist in track.artists])
        album = track.album.name
        indent = constants.INDENT + " " * 3
        year = track.album.year

        label = name
        if track.explicit:
            label += " [E]"
        if track.best_available_quality == "master":
            label += " [M]"
        label += f"\n{indent}{artists}\n{indent}{album}"
        if year:
            label += f" ({year})"
        if track.album.explicit:
            label += " [E]"
        if track.album.best_available_quality == "master":
            label += " [M]"
        return label

    def label_album(album: Album) -> str:
        name = album.name
        artists = ", ".join([artist.name for artist in album.artists])
        indent = constants.INDENT + " " * 3
        year = album.year

        label = name
        if year:
            label += f" ({year})"
        if album.explicit:
            label += " [E]"
        if album.best_available_quality == "master":
            label += " [M]"
        label += f"\n{indent}{artists}"
        return label

    def label_artist(artist: Artist) -> str:
        return artist.name

    labeler = {
        Track: label_track,
        Album: label_album,
        Artist: label_artist,
    }[media_type]

    choices = [questionary.Choice(labeler(result), value=result) for result in results]
    answer = questionary.select("Select one:", choices=choices).ask()
    if not answer:
        raise ManiaException("")
    return answer


def resolve_metadata(config: dict, track: Track, path: str, indent: int) -> None:
    """Embed tags and cover art from `track` to the file at `path`"""
    log(config, "Resolving metadata...", indent=indent)

    cover: Optional[metadata.Cover]
    if track.album.cover_url:
        request = requests.get(track.album.cover_url)
        request.raise_for_status()
        data = request.content
        mime = request.headers.get("Content-Type", "")
        cover = metadata.Cover(data, mime)
    else:
        cover = None

    {"mp4": metadata.resolve_mp4_metadata, "flac": metadata.resolve_flac_metadata}[
        track.file_extension
    ](config, track, path, cover)


def get_track_path(
    client: Client,
    config: dict,
    track: Track,
    siblings: List[Track] = None,
    include_artist: bool = False,
    include_album: bool = False,
) -> str:
    artist_path = ""
    album_path = ""
    disc_path = ""
    track_path = ""

    temporary_extension = f".{constants.TEMPORARY_EXTENSION}.{track.file_extension}"

    if include_artist or config["full-structure"]:
        artist_path = sanitize(config, track.album.artists[0].name)
        album_format_string = config["album-format"]
    else:
        album_format_string = config["individual-album-format"]

    siblings = siblings or client.get_album_tracks(track.album)
    maximum_disc_number = max(sibling.disc_number for sibling in siblings)
    maximum_track_number = max(sibling.track_number for sibling in siblings)
    if include_album or config["full-structure"]:
        if maximum_disc_number > 1:
            disc_number = str(track.disc_number).zfill(len(str(maximum_disc_number)))
            disc_path = sanitize(config, f"Disc {disc_number}")
        album_formatted = album_format_string.format(**track.album.format_dict())
        album_path = sanitize(config, album_formatted)
        track_format_string = config["track-format"]
    else:
        track_format_string = config["individual-track-format"]
    track_format_dict = track.format_dict(maximum_track_number=maximum_track_number)
    track_path = sanitize(
        config,
        track_format_string.format(**track_format_dict),
        length_padding=len(temporary_extension),
    )

    return os.path.join(
        config["output-directory"], artist_path, album_path, disc_path, track_path
    )


def download_track(
    client: Client,
    config: dict,
    track: Track,
    siblings: List[Track] = None,
    include_artist: bool = False,
    include_album: bool = False,
    indent: int = 0,
) -> None:
    track_path = get_track_path(
        client,
        config,
        track,
        siblings=siblings,
        include_artist=include_artist,
        include_album=include_album,
    )
    temporary_path = (
        f"{track_path}.{constants.TEMPORARY_EXTENSION}.{track.file_extension}"
    )
    final_path = f"{track_path}.{track.file_extension}"
    if os.path.isfile(final_path):
        log(
            config,
            f"Skipping download of {os.path.basename(final_path)}; it already exists.",
            indent=indent,
        )
        return
    try:
        media_url = client.get_media(track)
    except UnavailableException:
        log(
            config,
            f"Skipping download of {os.path.basename(final_path)}; track is not available. Perhaps it's region-locked?",
            indent=indent,
        )
        return
    os.makedirs(os.path.dirname(final_path), exist_ok=True)
    request = requests.get(media_url, stream=True)
    request.raise_for_status()
    with open(temporary_path, mode="wb") as temp_file:
        chunk_size = constants.DOWNLOAD_CHUNK_SIZE
        iterator = request.iter_content(chunk_size=chunk_size)
        if config["quiet"]:
            for chunk in iterator:
                temp_file.write(chunk)
        else:
            total = int(request.headers["Content-Length"])
            with tqdm(
                total=total,
                miniters=1,
                unit="B",
                unit_divisor=1024,
                unit_scale=True,
                dynamic_ncols=True,
            ) as progress_bar:
                for chunk in iterator:
                    temp_file.write(chunk)
                    progress_bar.update(chunk_size)

    if not config["skip-metadata"]:
        try:
            resolve_metadata(config, track, temporary_path, indent)
        except metadata.InvalidFileError:
            log(
                config,
                f"Skipping {os.path.basename(final_path)}; received invalid file",
                indent=indent,
            )
            os.remove(temporary_path)
            return
    os.rename(temporary_path, final_path)


def handle_track(client: Client, config: dict, query: str) -> None:
    track = cast(Track, search(client, config, Track, query))
    log(config, f'Downloading "{track.name}"...')
    download_track(client, config, track)


def download_album(
    client: Client,
    config: dict,
    album: Album,
    include_artist: bool = False,
    indent: int = 0,
) -> None:
    tracks = client.get_album_tracks(album)
    for index, track in enumerate(tracks, 1):
        log(
            config,
            f'Downloading "{track.name}" ({index} of {len(tracks)} track(s))...',
            indent=indent,
        )
        download_track(
            client,
            config,
            track,
            siblings=tracks,
            include_artist=include_artist,
            include_album=True,
            indent=indent + 1,
        )


def handle_album(client: Client, config: dict, query: str) -> None:
    album = cast(Album, search(client, config, Album, query))
    log(config, f'Downloading "{album.name}"...')
    download_album(client, config, album)


def download_artist(
    client: Client, config: dict, artist: Artist, indent: int = 0
) -> None:
    albums = client.get_artist_albums(artist)
    if config["include-eps-singles"]:
        eps_singles = client.get_artist_eps_singles(artist)
        albums = [*albums, *eps_singles]
    for index, album in enumerate(albums, 1):
        log(
            config,
            f'Downloading "{album.name}" ({index} of {len(albums)} album(s))...',
            indent=indent,
        )
        download_album(client, config, album, include_artist=True, indent=indent + 1)


def handle_artist(client: Client, config: dict, query: str) -> None:
    artist = cast(Artist, search(client, config, Artist, query))
    log(config, f'Downloading "{artist.name}"...')
    download_artist(client, config, artist)


def handle_url(client: Client, config: dict, url: str):
    try:
        media_type, media = client.resolve_url(url)
    except ValueError as error:
        raise ManiaSeriousException(str(error)) from error

    if media is None:
        raise ManiaSeriousException(f"Couldn't find anything at that URL.")

    log(config, f'Downloading "{media.name}"...')
    downloader = {
        Track: download_track,
        Album: download_album,
        Artist: download_artist,
    }[media_type]

    downloader(client, config, media)


def load_config(args: dict) -> dict:
    if args["config-path"]:
        config_path = args["config-path"]
    else:
        config_path = constants.CONFIG_PATH
        if not os.path.isfile(config_path):
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w") as config_file:
                config_file.write(constants.DEFAULT_CONFIG)

    config_toml = toml.load(config_path)

    def resolve(from_args, from_file, default):
        if from_args is not None:
            return from_args
        if from_file is not None:
            return from_file
        return default

    config = {
        key: resolve(args.get(key), config_toml.get(key), default)
        for key, default in constants.DEFAULT_CONFIG_TOML.items()
    }
    config["output-directory"] = os.path.expanduser(config["output-directory"])
    os.makedirs(config["output-directory"], exist_ok=True)
    config["config-path"] = config_path
    return config


def run() -> None:
    parser = argparse.ArgumentParser()

    handlers = {
        "track": handle_track,
        "album": handle_album,
        "artist": handle_artist,
        "url": handle_url,
    }
    parser.add_argument("command", choices=handlers.keys())

    parser.add_argument("--config-path", dest="config-path")

    for key, value in constants.DEFAULT_CONFIG_TOML.items():
        if isinstance(value, bool):
            boolean = parser.add_mutually_exclusive_group()

            # we don't use store_true/store_false here because we need the
            # default value to be None, not False/True.
            boolean.add_argument(f"--{key}", action="store_const", const=True, dest=key)
            boolean.add_argument(
                f"--no-{key}", action="store_const", const=False, dest=key
            )
        else:
            parser.add_argument(f"--{key}", nargs="?", dest=key)

    parser.add_argument("query", nargs="+")

    parsed_args = parser.parse_args()
    args = vars(parsed_args)

    config = load_config(args)

    if "username" in config or "password" in config:
        config_path = config["config-path"]
        log(
            config,
            f"Note: due to changes on TIDAL's end, login is now done by mimicking an Android TV, and directly specifying a username and password is no longer supported. You can remove them from your configuration file ({config_path}).",
        )
    try:
        with open(constants.SESSION_PATH, "r") as session_file:
            session_dict = toml.load(session_file)
        session = TidalSession(**session_dict)
        session.check_valid()
        log(config, "Loaded cached TIDAL session.")
    except (FileNotFoundError, toml.TomlDecodeError, TidalAuthError):
        log(config, "No valid cached session, creating a new one...")
        session = TidalSession()
        session.get_authorization()
        session.authenticate()

    client = TidalClient(config, session)

    try:
        handlers[args["command"]](client, config, " ".join(args["query"]))
    finally:
        log(config, "Saving TIDAL session for future use...")
        os.makedirs(os.path.dirname(constants.SESSION_PATH), exist_ok=True)
        with open(constants.SESSION_PATH, "w") as session_file:
            toml.dump(session.to_dict(), session_file)

    log(config, "Done!")


def main() -> None:
    """Handle exit codes and SIGINT"""
    try:
        run()
    except requests.exceptions.HTTPError:
        print("Uncaught HTTP Error:")
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
    except ManiaException as exception:
        if str(exception):
            print(exception, file=sys.stderr)
        sys.exit(exception.exit_code)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
