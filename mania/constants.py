import ruamel.yaml
import os

yaml = ruamel.yaml.YAML(typ="safe", pure=True)
yaml.default_flow_style = False

config_file = os.path.expanduser("~/.config/mania/config.yaml")
final_extension = "mp3"
track_digit_padding = 2
temporary_extension = "part.mp3"
default_config = {
	"username": None,
	"password": None,
	"quiet": False,
	"android-id": None,
	"skip-metadata": False,
	"increment-playcount": False,
	"search-count": 8,
	"quality": "hi",
	"output-directory": ".",
	"debug-logging": False,
	"lucky": False,
}
