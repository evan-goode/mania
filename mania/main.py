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

class NoResultsException(models.ManiaException):
    pass

class NoAnswerException(models.ManiaException):
    pass

def log(config, message="", indent=0):
    if message is not None and not config["quiet"]:
        print(constants.INDENT * indent + str(message))

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
        raise NoResultsException("No results found.", config)
    if config["lucky"]:
        return results[0]
    def song_handler(results):
        choices = []
        for result in results:
            provider = result.provider.name
            name = result.name
            artist = ", ".join([artist.name for artist in result.artists])
            album = result.album.name
            indent = constants.INDENT + " " * 3
            year = result.album.year
            label = (f"{name}\n{indent}{artist}\n{indent}{album} ({year}) [{provider}]\n")
            choices.append(questionary.Choice(label, value=result))
        return choices
    def album_handler(results):
        choices = []
        for result in results:
            provider = result.provider.name
            name = result.name
            artist = ", ".join([artist.name for artist in result.artists])
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
        raise NoAnswerException("", config)
    return answer

def resolve_metadata(config, song, path, indent):
    def get_picture(song):
        if not song.album.cover_art_url:
            return None
        request = requests.get(song.album.cover_art_url)
        request.raise_for_status()
        return {
            "data": request.content,
            "mime": request.headers.get("content-type", ""),
        }
    log(config, "Resolving metadata...", indent=indent)
    picture = get_picture(song)
    {
        # "mp3": metadata.resolve_mp3_metadata,
        "mp4": metadata.resolve_mp4_metadata,
        "flac": metadata.resolve_flac_metadata,
    }[song.extension](song, path, picture, config)

def get_song_path(client, config, song, siblings=None, include_artist=False, include_album=False):
    def get_maximum_disc_number(songs):
        return max([song.disc_number for song in songs])
    def get_maximum_track_number(songs):
        return max([song.track_number for song in songs])
    artist_path = ""
    album_path = ""
    disc_path = ""
    file_path = ""
    if include_artist or config["full-structure"]:
        artist_path = sanitize(config,
                               song.album.get_primary_artist_name(config))

    if include_album or config["full-structure"]:
        siblings = siblings if siblings else client.get_album_songs(song.album)
        maximum_disc_number = get_maximum_disc_number(siblings)
        maximum_track_number = get_maximum_track_number(siblings)
        album_path = sanitize(config, song.album.name)
        if maximum_disc_number > 1:
            disc_number = str(song.disc_number).zfill(len(str(maximum_disc_number)))
            disc_path = sanitize(config, f"Disc {disc_number}")
        track_number = str(song.track_number).zfill(len(str(maximum_track_number)))
        file_path = sanitize(config, f"{track_number} {song.name}")
    else:
        file_path = sanitize(config, song.name)

    return os.path.join(config["output-directory"], artist_path, album_path, disc_path, file_path)

def download_song(client, config, song,
                  siblings=None,
                  include_artist=False,
                  include_album=False,
                  indent=0):
    song_path = get_song_path(client, config, song,
                              siblings=siblings,
                              include_artist=include_artist,
                              include_album=include_album)
    temporary_path = f"{song_path}.{constants.TEMPORARY_EXTENSION}.{song.extension}"
    final_path = f"{song_path}.{song.extension}"
    if os.path.isfile(final_path):
        log(config,
            f"Skipping download of {os.path.basename(final_path)}; it already exists.",
            indent=indent)
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
    # if config["increment-play-count"] and getattr(song.provider, "increment_play_count", False):
    #    log(config, "Incrementing play count...", indent=indent)
    #    song.provider.increment_play_count(song)
    os.rename(temporary_path, final_path)

def handle_song(client, config, query):
    song = search(client, config, models.Song, query)
    log(config, f'Downloading "{song.name}"...')
    download_song(client, config, song)

def handle_album(client, config, query):
    album = search(client, config, models.Album, query)
    log(config, f'Downloading "{album.name}"...')
    download_album(client, config, album)

def download_album(client, config, album, include_artist=False, indent=0):
    songs = client.get_album_songs(album)
    for index, song in enumerate(songs, 1):
        log(config, f'Downloading "{song.name}" ({index} of {len(songs)} song(s))...', indent=indent)
        download_song(client, config, song,
                      siblings=songs,
                      include_artist=include_artist,
                      include_album=True,
                      indent=indent + 1)

def handle_discography(client, config, query):
    artist = search(client, config, models.Artist, query)
    log(config, f'Downloading "{artist.name}"...')
    download_discography(client, config, artist)

def download_discography(client, config, artist, indent=0):
    albums = client.get_artist_albums(artist)
    for index, album in enumerate(albums, 1):
        log(config, f'Downloading "{album.name}" ({index} of {len(albums)} album(s))...', indent=indent)
        download_album(client, config, album, include_artist=True, indent=indent + 1)

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
        config["output-directory"] = os.path.expanduser(config["output-directory"])
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
    except models.ManiaSeriousException as exception:
        if str(exception):
            log(exception.config, exception)
        sys.exit(exception.exit_code)
    except KeyboardInterrupt:
        sys.exit(1)
    except models.ManiaException as exception:
        if str(exception):
            log(exception.config, exception)
        sys.exit(exception.exit_code)
