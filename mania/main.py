import cursor
import requests
import progress.bar
import argparse
import os
import sys
import whaaaaat

import eyed3
eyed3.log.setLevel("ERROR")

from mania import authentication
from mania import constants

def log(config, message="", indent=0):
	if config["quiet"]:
		return
	print(constants.indent * indent + message)

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
	search = client.search(string, config["search-count"])
	results = search[f"{media_type}_hits"]
	if not results:
		log(config, "No results found.")
		sys.exit(2)
	if config["lucky"]:
		return results[0]
	def song_handler(results):
		choices = []
		for result in results:
			title = result["track"]["title"]
			artist = result["track"]["artist"]
			album = result["track"]["album"]
			year = result["track"]["year"]
			indent = constants.indent + " " * 3
			label = f"{title}\n{indent}{artist}\n{indent}{album} ({year})\n"
			choices.append({"name": label, "value": result, "short": title})
		return choices
	def album_handler(results):
		choices = []
		for result in results:
			name = result["album"]["name"]
			artist = result["album"]["artist"]
			year = result["album"]["year"]
			indent = constants.indent + " " * 3
			label = f"{name} ({year})\n{indent}{artist}\n"
			choices.append({"name": label, "value": result, "short": name})
		return choices
	def artist_handler(results):
		choices = []
		for result in results:
			name = result["artist"]["name"]
			label = name
			choices.append({"name": label, "value": result, "short": name})
		return choices
	media_handlers = {"song": song_handler,
	                  "album": album_handler,
	                  "artist": artist_handler}
	choices = media_handlers[media_type](results)
	questions = [{"type": "list",
	              "name": "choice",
                  "message": "Select one:",
                  "choices": choices}]
	answer = whaaaaat.prompt(questions)
	if "choice" not in answer:
		sys.exit(1)
	return answer["choice"]

def song(client, config, query):
	song_object = search(client, config, "song", query)
	song_title = sanitize(config, song_object["track"]["title"])
	song_id = song_object["track"]["storeId"]

	path = "/".join([config["output-directory"], song_title])
	download_song(client, config, song_object["track"], path)

def download_song(client, config, song_object, song_path, indent=0):
	temporary_path = ".".join([song_path, constants.temporary_extension])
	final_path = ".".join([song_path, constants.final_extension])
	if os.path.isfile(final_path):
		log(config,
		    f"Skipping {os.path.basename(final_path)}; it already exists.",
		    indent=indent)
		return
	song_id = song_object["storeId"]
	stream_url = client.get_stream_url(song_id, quality=config["quality"])
	os.makedirs(os.path.dirname(final_path), exist_ok=True)
	request = requests.get(stream_url, stream=True)
	request.raise_for_status()
	with open(temporary_path, mode="wb") as pointer:
		chunk_size = 4096
		length = int(request.headers.get("content-length")) / chunk_size
		bar = None
		if not config["quiet"]:
			bar = progress.bar.IncrementalBar(constants.indent * indent +
			                                  os.path.basename(final_path),
			                                  max=length,
			                                  suffix="%(percent).f%%")
		for chunk in request.iter_content(chunk_size=chunk_size):
			pointer.write(chunk)
			if bar:
				bar.next()
		log(config)
	if not config["skip-metadata"]:
		log(config, "Resolving metadata...", indent=indent)
		request = requests.get(song_object["albumArtRef"][0]["url"])
		file = eyed3.load(temporary_path)
		file.initTag()
		file.tag.title = song_object["title"]
		file.tag.artist = song_object["artist"]
		file.tag.album = song_object["album"]
		file.tag.album_artist = song_object["albumArtist"]
		file.tag.track_num = song_object["trackNumber"]
		file.tag.genre = song_object["genre"]
		file.tag.images.set(3, request.content, "image/jpeg")
		file.tag.save()
	if config["increment-playcount"]:
		log(config, "Incrementing playcount...", indent=indent)
		client.increment_song_playcount(song_object["storeId"])
	os.rename(temporary_path, final_path)

def album(client, config, query):
	lite_album_object = search(client, config, "album", query)
	album_id = lite_album_object["album"]["albumId"]
	album_object = client.get_album_info(album_id, include_tracks=True)
	album_title = sanitize(config, album_object["name"])
	path = "/".join([config["output-directory"], album_title])
	download_album(client, config, album_object, path)

def download_album(client, config, album_object, album_path, indent=0):
	tracks = album_object["tracks"]
	total_count = len(tracks)
	track_count = max(tracks, key=lambda track: track["trackNumber"])["trackNumber"]
	disc_count = max(tracks, key=lambda track: track["discNumber"])["discNumber"]
	track_digits = len(str(track_count))
	disc_digits = len(str(disc_count))

	for index, song_object in enumerate(tracks):
		song_title = sanitize(config, song_object["title"])
		song_id = song_object["storeId"]

		song_file_name = None
		if track_count > 1:
			song_track_number = str(song_object["trackNumber"]).zfill(track_digits)
			song_file_name = sanitize(config, f"{song_track_number} - {song_title}")
		else:
			song_file_name = sanitize(config, song_title)

		song_path = None
		if disc_count > 1:
			disc_name = sanitize(config, f"Disc {str(song_object['discNumber']).zfill(disc_digits)}")
			song_path = "/".join([album_path, disc_name, song_file_name])
		else:
			song_path = "/".join([album_path, song_file_name])

		display_title = song_object["title"]
		log_string = " ".join([f'Downloading "{display_title}"',
		                       f"({index + 1} of {total_count} song(s))..."])
		log(config, log_string, indent=indent)
		# numbering starts at zero, Dijkstra said, it'll be better, he said
		download_song(client, config, song_object, song_path, indent=indent + 1)

def discography(client, config, query):
	lite_artist_object = search(client, config, "artist", query)
	artist_id = lite_artist_object["artist"]["artistId"]
	artist_object = client.get_artist_info(artist_id,
	                                       include_albums=True,
	                                       max_top_tracks=0,
	                                       max_rel_artist=0)
	artist_name = sanitize(config, artist_object["name"])
	total_count = len(artist_object['albums'])
	for index, lite_album_object in enumerate(artist_object["albums"]):
		album_id = lite_album_object["albumId"]
		album_object = client.get_album_info(album_id, include_tracks=True)
		album_name = sanitize(config, album_object["name"])
		path = "/".join([config["output-directory"], artist_name, album_name])
		display_name = album_object["name"]
		log_string = " ".join([f'Downloading "{display_name}"',
		                       f"({index + 1} of {total_count} album(s))..."])
		log(config, log_string)
		download_album(client, config, album_object, path, indent=1)

def load_config(args):
	def initialize(config_file):
		config_file = constants.config_file
		if not os.path.isfile(config_file):
			os.makedirs(os.path.dirname(config_file), exist_ok=True)
			with open(config_file, "w") as config_pointer:
				constants.yaml.dump(constants.default_config, config_pointer)
		return config_file
	config_file = args["config-file"] or initialize(constants.default_config)
	with open(config_file) as config_pointer:
		file = constants.yaml.load(config_pointer) or {}
		def resolve(from_args, from_file, default):
			if from_args != None:
				return from_args
			if from_file != None:
				return from_file
			return default
		config = {key: resolve(args.get(key), file.get(key), default)
		          for key, default in constants.default_config.items()}
		output_directory = os.path.expanduser(config["output-directory"])
		config["output-directory"] = output_directory
		return config

def main():
	parser = argparse.ArgumentParser()
	handlers = {"song": song,
	            "album": album,
	            "discography": discography}
	subparsers = parser.add_subparsers(dest="query")
	subparsers.required = True
	for name, handler in handlers.items():
		subparser = subparsers.add_parser(name)
		subparser.add_argument("query", nargs="+")
		for key, value in constants.default_config.items():
			if type(value) == bool:
				boolean = subparser.add_mutually_exclusive_group()
				boolean.add_argument(f"--{key}", action="store_true", dest=key)
				boolean.add_argument(f"--no-{key}", action="store_false", dest=key)
				continue
			subparser.add_argument(f"--{key}", nargs="?", dest=key)
		subparser.add_argument("--config-file", dest="config-file")
		subparser.set_defaults(func=handler)

	parsed_args = parser.parse_args()
	args = vars(parsed_args)
	config = load_config(args)

	log(config, "Authenticating...")
	client = authentication.authenticate(config)

	parsed_args.func(client, config, args["query"])
	log(config, "Done!")

def execute():
	try:
		main()
	except KeyboardInterrupt:
		sys.exit(1)
	finally:
		cursor.show()
