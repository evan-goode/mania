# Mania 👻

Mania is a command-line tool for downloading music from streaming services. It currently supports [Google Play Music](https://play.google.com/music) and [TIDAL](https://tidal.com). It is intended for educational and private use only, and **not** as a tool for pirating and distributing music.

## Installation :arrow_down:

```
pip install --user "https://github.com/evan-goode/mania/archive/master.zip"
```

Mania requires Python 3.6 or higher. Support for older versions isn't on the roadmap, but feel free to PR. I don't think much would need to be changed.

Mania has only been tested on macOS and GNU/Linux.

## Usage :muscle:

Download a song, an album, or even an artist's entire discography from TIDAL:

```
mania song the great gig in the sky --tidal
mania album the dark side of the moon --tidal
mania discography pink floyd --tidal
```

Options go anywhere _after_ the verb. For example, to automatically select the top search result:

```
mania song fake plastic trees --tidal --lucky
```

## Configuration :wrench:

Every option (except `--config-file`) can be specified either as a command-line argument or using a YAML configuration file. On the command line, prefix the option with `--`, or, when setting a boolean to false, `--no-`.

The first time it is run, Mania populates `~/config/mania/config.yaml` with some default values. For more information on the YAML format, see https://docs.ansible.com/ansible/latest/YAMLSyntax.html.

To point Mania to a different configuration file, use `--config-file <file>`.

- `google`: enable downloading from Google Play Music
- `google-username`: your Google username. If this is not specified, Mania will ask at runtime. Default value is `null`.
- `google-password`: your Google password. Again, if this is not specified, Mania will ask. If you use two-factor authentication, you will need to supply an [App Password](https://support.google.com/accounts/answer/185833?hl=en) instead. Default value is `null`.
- `google-android-id`: refer to the [gmusicapi documentation](https://unofficial-google-music-api.readthedocs.io/en/latest/reference/mobileclient.html?highlight=android_id#gmusicapi.clients.Mobileclient.login). Default value is `null`.
- `google-quality`: Default value is `high`. Possible values are `high` (320 kbps MP3), `medium` (160 kbps MP3), and `low` (96 kbps MP3).
- `tidal`: enable downloading from TIDAL
- `tidal-username`: your TIDAL username. If this is not specified, Mania will ask at runtime. Default value is `null`.
- `tidal-password`: your TIDAL password. Again, if this is not specified, Mania will ask. Default value is `null`.
- `tidal-quality`: Default value is `lossless`. Possible values are `lossless` (1411 kbps FLAC), `high` (320 kbps AAC), and `low` (96 kbps AAC). Note that `lossless` requires a TIDAL HiFi subscription.
- `quiet`: don't log any output. Default value is `false`.
- `nice-format`: rename downloaded material to mv /be kebab-case. "Maxwell's Silver Hammer (Remastered).mp3" becomes "maxwells-silver-hammer-remastered.mp3". Default value is `false`.
- `skip-metadata`: don't download cover art or set tags. Not sure why someone would want this. Default value is `false`.
- `full-structure`: always organize content by artist and album. Default value is `false`.
- `increment-play-count`: increment each song's "play count" by one after downloading. Currently only applies to Google. Default value is `true`.
- `search-count`: how many results from each provider to include in the search. Default value is `8`.
- `output-directory`: where to put downloaded music. Default value is `.` (your working directory when you run Mania).
- `debug-logging`: enable debug logging if the provider supports it. Default value is `false`.
- `lucky`: automatically select the top hit. Default value is `false`.

## See Also :books:

- [tidalapi4mopidy](https://github.com/mones88/python-tidal)
- [tidalapi](https://github.com/tamland/python-tidal)
- [gmusicapi](https://unofficial-google-music-api.readthedocs.io/en/latest/)
- [gmusicproxy](https://gmusicproxy.net/)
