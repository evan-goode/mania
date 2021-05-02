"""Global constants and default configuration"""

import os

import toml

PROGRAM_NAME = "mania"
config_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
cache_home = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))

CACHE_DIR = os.path.join(cache_home, PROGRAM_NAME)
CONFIG_DIR = os.path.join(config_home, PROGRAM_NAME)

SESSION_PATH = os.path.join(CACHE_DIR, "session.toml")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.toml")
INDENT = "  "
TEMPORARY_EXTENSION = "part"
DOWNLOAD_CHUNK_SIZE = 1024
DEFAULT_CONFIG = """quality = "lossless"
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
