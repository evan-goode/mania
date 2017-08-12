# Mania 👻
Mania is a command-line tool for downloading music from [Google Play Music](http://play.google.com/music), based on the fabulous [Unofficial Google Play Music API](https://github.com/simon-weber/gmusicapi).

Mania doesn't work miracles; it still requires a Google Play Music subscription, but it lets you get the most from your money. All-you-can-eat DRM-free 320 kbps MP3 files for $9.99/month isn't too bad of a deal.

Use at your own risk.

## Installation :arrow_down:
_Possibly coming soon to [PyPI](https://pypi.python.org/pypi)!_

Mania requires Python 3.6 or higher. Support for older versions isn't on the roadmap, but feel free to PR. I don't think much would need to be changed.

```
pip3 install "https://github.com/evan-goode/mania/archive/master.zip"
```

Mania has only been tested on macOS and Linux.

## Usage :muscle:
Download a song, an album, or an artist's entire discography:

```
mania song the great gig in the sky
mania album the dark side of the moon
mania discography pink floyd
```

Options go anywhere _after_ the subcommand. For example, to automatically select the top hit:
```
mania song fake plastic trees --lucky
```

## Notes :memo:
- As far as I know, Mania files are not watermarked, but Google could change their back end at any time without notice. Before sharing Mania files publicly, you may want to compare them with the same songs downloaded using other accounts.

## Configuration :wrench:
Every option (except `--config-file`, of course) can be specified either as a command-line argument (by prefixing it with `--`), or using a YAML configuration file. 

When it's first run, Mania creates `~/config/mania/config.yaml` and populates it with some default values. For more information on the YAML format, see http://docs.ansible.com/ansible/latest/YAMLSyntax.html.

To point Mania to a different configuration file, use `--config-file <file>`

- `username`: your Google username. If this is not specified, Mania will ask at runtime. Default value is `null`.
- `password`: your Google password. Again, if this is not specified, Mania will ask. If you use two-factor authentication, you will need to supply an [App Password](https://support.google.com/accounts/answer/185833?hl=en) instead. Default value is `null`.
- `quiet`: don't log any output. Default value is `false`.
- `nice-format`: make file and directory names a little nicer. "Maxwell's Silver Hammer (Remastered).mp3" becomes "maxwells-silver-hammer-remastered.mp3". Default value is `false`.
- `android-id`: refer to the [gmusicapi documentation](http://unofficial-google-music-api.readthedocs.io/en/latest/reference/mobileclient.html?highlight=android_id#gmusicapi.clients.Mobileclient.login). Default value is `null`.
- `skip-metadata`: don't download album art or set ID3 tags. Not sure why someone would want this. Default value is `false`.
- `increment-playcount`: increment each song's `playcount` variable by one after downloading. Google may use this variable to decide how much artists get paid. It's not clear. Default value is `false`.
- `search-count`: how many results to include in the search. Default value is `8`.
- `quality`: refer to the [gmusicapi documentation](http://unofficial-google-music-api.readthedocs.io/en/latest/reference/mobileclient.html?highlight=quality#gmusicapi.clients.Mobileclient.get_stream_url). Default value is `hi`. Possible values are `hi`, `med`, and `low`.
- `output-directory`: where to put downloaded music. Default value is `.` (the directory from which Mania was run).
- `debug-logging`: enable gmusicapi's debug logging. Default value is `false`.
- `lucky`: automatically select the top hit. Default value is `false`.

## See Also :books:
* [gmusicapi](https://unofficial-google-music-api.readthedocs.io/en/latest/)
* [gmusicproxy](http://gmusicproxy.net/)
