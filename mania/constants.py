import os

import toml

CONFIG_PATH = os.path.expanduser("~/.config/mania/config.toml")
INDENT = "  "
TEMPORARY_EXTENSION = "part"
DOWNLOAD_CHUNK_SIZE = 1024
DEFAULT_CONFIG = """username = ""
password = ""

quality = "lossless"
output-directory = "."
by-id = false
lucky = false
search-count = 16
quiet = false
nice-format = false
full-structure = false
skip-metadata = false
"""
DEFAULT_CONFIG_TOML = toml.loads(DEFAULT_CONFIG)
