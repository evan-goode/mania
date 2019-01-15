import ruamel.yaml
import os

YAML = ruamel.yaml.YAML(typ="safe", pure=True)
YAML.default_flow_style = False

CONFIG_FILE = os.path.expanduser("~/.config/mania/config.yaml")
INDENT = "  "
TEMPORARY_EXTENSION = "part"
CHUNK_SIZE = 1024
DEFAULT_CONFIG = {
    "tidal": False,
    "tidal-username": None,
    "tidal-password": None,
    "tidal-quality": "lossless",
    "lucky": False,
    "quiet": False,
    "nice-format": False,
    "full-structure": False,
    "skip-metadata": False,
    "increment-play-count": True,
    "search-count": 8,
    "output-directory": ".",
    "debug-logging": False,
}
