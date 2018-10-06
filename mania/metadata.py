import mutagen
from mutagen.mp4 import MP4, MP4Cover as MP4Picture
from mutagen.id3 import ID3, APIC as ID3Picture
from mutagen.flac import FLAC, Picture as FLACPicture

class InvalidFileError(Exception):
    pass

def resolve_mp3_metadata(song, path, picture):
    tagger = mutagen.File(path, easy=True)
    tagger.add_tags()
    tagger["title"] = song.name
    tagger["album"] = song.album.name
    tagger["artist"] = song.artist.name
    tagger["albumartist"] = song.album.artist.name
    tagger["tracknumber"] = str(song.track_number)
    tagger.save()
    tagger = ID3(path)
    tagger["APIC"] = ID3Picture(
        encoding=3,
        type=3,
        desc=u'Cover',
        mime=picture["mime"],
        data=picture["data"],
    )
    tagger.save()

def resolve_mp4_metadata(song, path, picture):
    tagger = MP4(path)
    tagger["\xa9nam"] = song.name
    tagger["\xa9alb"] = song.album.name
    tagger["\xa9ART"] = song.artist.name
    tagger["aART"] = song.album.artist.name
    tagger["trkn"] = [(song.track_number, 1)]
    imageformat = (MP4Picture.FORMAT_PNG
                   if picture["mime"] == "image/png"
                   else MP4Picture.FORMAT_JPEG)
    tagger["covr"] = [MP4Picture(picture["data"], imageformat=imageformat)]
    tagger.save()

def resolve_aac_metadata(song, path, picture):
    tagger = mutagen.File(path, easy=True)
    tagger.add_tags()
    tagger["title"] = song.name
    tagger["album"] = song.album.name
    tagger["artist"] = song.artist.name
    tagger["albumartist"] = song.album.artist.name
    tagger["tracknumber"] = str(song.track_number)
    tagger.save()
    tagger = ID3(path)
    tagger["APIC"] = ID3Picture(
        encoding=3,
        type=3,
        desc=u'Cover',
        mime=picture["mime"],
        data=picture["data"],
    )
    tagger.save()

def resolve_flac_metadata(song, path, picture):
    try:
        tagger = FLAC(path)
    except mutagen.flac.FLACNoHeaderError:
        raise InvalidFileError()
    tagger["title"] = song.name
    tagger["album"] = song.album.name
    tagger["artist"] = song.artist.name
    tagger["albumartist"] = song.album.artist.name
    tagger["tracknumber"] = str(song.track_number)
    flac_picture = FLACPicture()
    flac_picture.type = 3
    flac_picture.desc = "Cover"
    flac_picture.mime = picture["mime"]
    flac_picture.data = picture["data"]
    tagger.add_picture(flac_picture)
    tagger.save()
