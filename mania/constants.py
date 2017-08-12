import ruamel.yaml
import os

yaml = ruamel.yaml.YAML(typ="safe", pure=True)
yaml.default_flow_style = False

config_file = os.path.expanduser("~/.config/mania/config.yaml")
final_extension = "mp3"
track_digit_padding = 2
indent = "  "
temporary_extension = "part.mp3"
default_config = {
	"username": None,
	"password": None,
	"quiet": False,
	"nice-format": False,
	"android-id": None,
	"skip-metadata": False,
	"increment-playcount": True,
	"search-count": 8,
	"quality": "hi",
	"output-directory": ".",
	"debug-logging": False,
	"lucky": False,
}
