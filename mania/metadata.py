import mutagen
from mutagen.mp4 import MP4, MP4Cover as MP4Picture
from mutagen.flac import FLAC, Picture as FLACPicture
from typing import NamedTuple, Optional

from .models import Track, Album, Artist


class InvalidFileError(Exception):
    pass


class Cover(NamedTuple):
    data: bytes
    mime: str


def resolve_mp4_metadata(
    config: dict, track: Track, path: str, cover: Optional[Cover]
) -> None:
    tagger = MP4(path)
    tagger["\xa9nam"] = track.name
    tagger["\xa9alb"] = track.album.name
    tagger["\xa9ART"] = [artist.name for artist in track.artists]
    tagger["aART"] = [artist.name for artist in track.album.artists]
    tagger["trkn"] = [(track.track_number, 0)]
    tagger["disk"] = [(track.disc_number, 0)]
    if cover:
        imageformat = {
            "image/png": MP4Picture.FORMAT_PNG,
            "image/jpeg": MP4Picture.FORMAT_JPEG,
        }[cover.mime]
        tagger["covr"] = [MP4Picture(cover.data, imageformat=imageformat)]
    tagger.save()


def resolve_flac_metadata(
    config: dict, track: Track, path: str, cover: Optional[Cover]
) -> None:
    try:
        tagger = FLAC(path)
    except mutagen.flac.FLACNoHeaderError:
        raise InvalidFileError()
    tagger["title"] = track.name
    tagger["album"] = track.album.name
    tagger["artist"] = [artist.name for artist in track.artists]
    tagger["albumartist"] = [artist.name for artist in track.album.artists]
    tagger["tracknumber"] = str(track.track_number)
    tagger["discnumber"] = str(track.disc_number)
    if cover:
        flac_picture = FLACPicture()
        flac_picture.type = 3
        flac_picture.desc = "Cover"
        flac_picture.mime = cover.mime
        flac_picture.data = cover.data
        tagger.add_picture(flac_picture)
    tagger.save()
