import sys
import os
import math
import argparse
import requests
import questionary
from tqdm import tqdm

from . import constants
from . import bridge
from . import models
from . import metadata

# exit codes:
# 1: graceful, expected exit, but still non-zero
# 2: unexpected error

def log(config, message="", indent=0):
    if not config["quiet"]:
        print(constants.INDENT * indent + message)

def sanitize(config, string):
    if not config["nice-format"]:
        illegal_symbols = ["/"]
        return "".join([symbol for symbol in string
                        if symbol not in illegal_symbols])
    alphanumeric = "".join([character for character in string
                            if character.isalnum() or character in [" ", "-"]])
    hyphenated = alphanumeric.replace(" ", "-")
    return "-".join([word for word in hyphenated.split("-")
                     if word]).lower()

def search(client, config, media_type, query):
    log(config, "Searching...")
    string = " ".join(query)
    results = client.search(string, media_type, config["search-count"])
    if not results:
        log(config, "No results found.")
        sys.exit(1)
    if config["lucky"]:
        return results[0]
    def song_handler(results):
        choices = []
        for result in results:
            provider = result.provider.name
            name = result.name
            artist = result.artist.name
            album = result.album.name
            indent = constants.INDENT + " " * 3
            year = result.year
            label = (f"{name}\n{indent}{artist}\n{indent}{album} ({year}) [{provider}]\n"
                     if year else f"{name}\n{indent}{artist}\n{indent}{album} [{provider}]\n")
            choices.append(questionary.Choice(label, value=result))
        return choices
    def album_handler(results):
        choices = []
        for result in results:
            provider = result.provider.name
            name = result.name
            artist = result.artist.name
            indent = constants.INDENT + " " * 3
            year = result.year
            label = (f"{name} ({year})\n{indent}{artist} [{provider}]\n"
                     if year else f"{name}\n{indent}{artist} [{provider}]\n")
            choices.append(questionary.Choice(label, value=result))
        return choices
    def artist_handler(results):
        choices = []
        for result in results:
            provider = result.provider.name
            name = result.name
            label = f"{name} [{provider}]"
            choices.append(questionary.Choice(label, value=result))
        return choices
    media_handlers = {models.Song: song_handler,
                      models.Album: album_handler,
                      models.Artist: artist_handler}
    answer = questionary.select(
        "Select one:",
        choices=media_handlers[media_type](results)
    ).ask()
    if not answer:
        sys.exit(1)
    return answer

def resolve_metadata(config, song, path, indent):
    log(config, "Resolving metadata...", indent=indent)
    request = requests.get(song.album.cover_art_url)
    request.raise_for_status()
    picture = {
        "data": request.content,
        "mime": request.headers.get("content-type", ""),
    }
    {
        "mp3": metadata.resolve_mp3_metadata,
        "mp4": metadata.resolve_mp4_metadata,
        "flac": metadata.resolve_flac_metadata,
    }[song.extension](song, path, picture)

def download_song(client, config, song, song_path, indent=0):
    temporary_path = f"{song_path}.{constants.TEMPORARY_EXTENSION}.{song.extension}"
    final_path = f"{song_path}.{song.extension}"
    if os.path.isfile(final_path):
        log(config,
            f"Skipping download of {os.path.basename(final_path)}; it already exists.",
            indent=indent)
        if not config["skip-metadata"]:
            # We try to update metadata even when a song is already downloaded
            # because more is known about a song while downloading the entire
            # album, for example the album artist, track number, and disc
            # number. In the event that a user downloads one song from an album
            # and then proceeds to download the whole album, that first song's
            # metadata should be updated to remain consistent with the rest of
            # the files.
            log(config, f"Attempting to update metadata...")
            try:
                resolve_metadata(config, song, final_path, indent)
            except metadata.InvalidFileError:
                log(f"{os.path.basename(final_path)} is invalid.")
        return
    try:
        media_url = client.get_media_url(song)
    except requests.exceptions.HTTPError as error:
        if error.response.status_code == 401:
            log(config,
                f"Skipping download of {os.path.basename(final_path)}; received HTTP 401 Unauthorized",
                indent=indent)
            return
        raise error
    os.makedirs(os.path.dirname(final_path), exist_ok=True)
    request = requests.get(media_url, stream=True)
    request.raise_for_status()
    with open(temporary_path, mode="wb") as pointer:
        chunk_size = constants.CHUNK_SIZE
        iterator = request.iter_content(chunk_size=chunk_size)
        if not config["quiet"]:
            total = math.ceil(int(request.headers.get("content-length")) / chunk_size)
            iterator = tqdm(iterator, total=total, unit='KiB', unit_scale=True)
        for chunk in iterator:
            pointer.write(chunk)
    if not config["skip-metadata"]:
        try:
            resolve_metadata(config, song, temporary_path, indent)
        except metadata.InvalidFileError:
            log(config,
                f"Skipping {os.path.basename(final_path)}; received invalid file",
                indent=indent)
            os.remove(temporary_path)
            return
    #if config["increment-play-count"] and getattr(song.provider, "increment_play_count", False):
    #    log(config, "Incrementing play count...", indent=indent)
    #    song.provider.increment_play_count(song)
    os.rename(temporary_path, final_path)

def get_song_path(config, song, track_count=1, disc_count=1):
    file_name = None
    if track_count > 1:
        track_number = str(song.track_number).zfill(len(str(track_count)))
        file_name = sanitize(config, f"{track_number} {song.name}")
    else:
        file_name = sanitize(config, song.name)
    if disc_count > 1:
        disc_number = str(song.disc_number).zfill(len(str(disc_count)))
        disc_name = sanitize(config, f"Disc {disc_number}")
        return os.path.join(disc_name, file_name)
    return file_name

def handle_song(client, config, query):
    song = search(client, config, models.Song, query)
    path = None
    if config["full-structure"]:
        siblings = client.get_album_songs(song.album)
        maximum_track_number = get_maximum_track_number(siblings)
        maximum_disc_number = get_maximum_disc_number(siblings)
        song_path = get_song_path(config, song,
                                  track_count=maximum_track_number,
                                  disc_count=maximum_disc_number)
        path = os.path.join(config["output-directory"],
                            sanitize(config, song.album.artist.name),
                            sanitize(config, song.album.name),
                            song_path)
    else:
        path = os.path.join(config["output-directory"],
                            get_song_path(config, song))
    download_song(client, config, song, path)

def handle_album(client, config, query):
    album = search(client, config, models.Album, query)
    path = None
    if config["full-structure"]:
        path = os.path.join(config["output-directory"],
                            sanitize(config, album.artist.name),
                            sanitize(config, album.name))
    else:
        path = os.path.join(config["output-directory"],
                            sanitize(config, album.name))
    download_album(client, config, album, path)

def get_maximum_track_number(songs):
    return max([song.track_number for song in songs])
def get_maximum_disc_number(songs):
    return max([song.disc_number for song in songs])

def download_album(client, config, album, album_path, indent=0):
    songs = client.get_album_songs(album)
    maximum_track_number = get_maximum_track_number(songs)
    maximum_disc_number = get_maximum_disc_number(songs)
    total_count = len(songs)
    for index, song in enumerate(songs, 1):
        song_path = get_song_path(config, song,
                                  track_count=maximum_track_number,
                                  disc_count=maximum_disc_number)
        path = os.path.join(album_path, song_path)
        log_string = " ".join([f'Downloading "{song.name}"',
                               f"({index} of {total_count} song(s))..."])
        log(config, log_string, indent=indent)
        download_song(client, config, song, path, indent=indent + 1)

def handle_discography(client, config, query):
    artist = search(client, config, models.Artist, query)
    path = os.path.join(
        config["output-directory"],
        sanitize(config, artist.name))
    download_discography(client, config, artist, path)

def download_discography(client, config, artist, artist_path, indent=0):
    albums = client.get_artist_albums(artist)
    total_count = len(albums)
    for index, album in enumerate(albums, 1):
        path = os.path.join(artist_path, sanitize(config, album.name))
        log_string = " ".join([f'Downloading "{album.name}"',
                               f"({index} of {total_count} album(s))..."])
        log(config, log_string, indent=indent)
        download_album(client, config, album, path, indent=indent + 1)

def load_config(args):
    def initialize(config_file):
        config_file = constants.CONFIG_FILE
        if not os.path.isfile(config_file):
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, "w") as config_pointer:
                constants.YAML.dump(constants.DEFAULT_CONFIG, config_pointer)
        return config_file
    config_file = args["config-file"] or initialize(constants.DEFAULT_CONFIG)
    with open(config_file) as config_pointer:
        file = constants.YAML.load(config_pointer) or {}
        def resolve(from_args, from_file, default):
            if from_args is not None:
                return from_args
            if from_file is not None:
                return from_file
            return default
        config = {key: resolve(args.get(key), file.get(key), default)
                  for key, default in constants.DEFAULT_CONFIG.items()}
        output_directory = os.path.expanduser(config["output-directory"])
        config["output-directory"] = output_directory
        config["config-file"] = config_file
        return config

def main():
    parser = argparse.ArgumentParser()
    handlers = {"song": handle_song,
                "album": handle_album,
                "discography": handle_discography,
                "artist": handle_discography}
    subparsers = parser.add_subparsers(dest="query")
    subparsers.required = True
    for name, handler in handlers.items():
        subparser = subparsers.add_parser(name)
        subparser.add_argument("query", nargs="+")
        for key, value in constants.DEFAULT_CONFIG.items():
            if isinstance(value, bool):
                boolean = subparser.add_mutually_exclusive_group()
                # we don't use store_true/store_false here because we need the
                # default value to be None, not False/True.
                boolean.add_argument(f"--{key}",
                                     action="store_const",
                                     const=True,
                                     dest=key)
                boolean.add_argument(f"--no-{key}",
                                     action="store_const",
                                     const=False,
                                     dest=key)
            else:
                subparser.add_argument(f"--{key}", nargs="?", dest=key)
        subparser.add_argument("--config-file", dest="config-file")
        subparser.set_defaults(func=handler)

    parsed_args = parser.parse_args()
    args = vars(parsed_args)
    config = load_config(args)

    log(config, "Authenticating...")
    client = bridge.Bridge(config)

    parsed_args.func(client, config, args["query"])
    log(config, "Done!")

def execute():
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
    except bridge.NoProvidersException as exception:
        print(exception)
        sys.exit(2)
    # except Exception as exception: # pylint: disable=W0703
    #     print(exception, file=sys.stderr)
    #     sys.exit(1)
