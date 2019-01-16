# Mania 👻

Mania is a command-line tool for downloading music from [TIDAL](https://tidal.com). It is intended for educational and private use only, and **not** as a tool for pirating and distributing music.

### A note about Google Play Music

Starting with version 3.0.0, Mania no longer supports Google Play Music. Why not? First and foremost, I no longer have a Google Play Music account, so GPM integration has become difficult to test. Second, the future of Google Play Music itself is uncertain. Google's reputation for killing off underperforming projects is [well-established](https://killedbygoogle.com/), and rumors of YouTube Music completely replacing GPM have recently resurfaced.

That being said, please let me know if you are interested in keeping Google Play Music supported. All I need is a GPM subscription or a volunteer who can test changes with their account.

## Installation :arrow_down:

```
pip3 install --user --upgrade "https://github.com/evan-goode/mania/archive/master.zip"
```

Mania requires Python 3.6 or higher. Support for older versions isn't on the roadmap, but feel free to submit a pull request. I don't think much would need to change.

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

- `tidal`: enable downloading from TIDAL
- `tidal-username`: your TIDAL username. If this is not specified, Mania will ask at runtime. Default value is `null`.
- `tidal-password`: your TIDAL password. Again, if this is not specified, Mania will ask. Default value is `null`.
- `tidal-quality`: Default value is `lossless`. Possible values are `lossless` (1411 kbps FLAC), `high` (320 kbps AAC), and `low` (96 kbps AAC). Note that `lossless` requires a TIDAL HiFi subscription.
- `quiet`: don't log any output. Default value is `false`.
- `nice-format`: rename downloaded material to follow kebab-case. "Maxwell's Silver Hammer (Remastered).mp3" becomes "maxwells-silver-hammer-remastered.mp3". Default value is `false`.
- `skip-metadata`: don't download cover art or set tags. Not sure why someone would want this. Default value is `false`.
- `full-structure`: always organize content by artist and album. Default value is `false`.
- `search-count`: how many results from each provider to include in the search. Default value is `8`.
- `output-directory`: where to put downloaded music. Default value is `.` (your working directory when you run Mania).
- `debug-logging`: enable debug logging if the provider supports it. Default value is `false`.
- `lucky`: automatically select the top hit. Default value is `false`.
- `various-artists`: tag songs and albums with multiple artists as "Various Artists" instead of by the first listed artist. Default value is `true`.

## License ⚖️

[The Unlicense](https://unlicense.org)

## See Also :books:

- [tidalapi4mopidy](https://github.com/mones88/python-tidal)
- [tidalapi](https://github.com/tamland/python-tidal)
