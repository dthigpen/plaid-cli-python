import os
from dotenv import load_dotenv, find_dotenv
import json
from pathlib import Path
import copy
DEFAULT_APP_DIR = Path.home() / ".plaid-cli-python"
DEFAULT_APP_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_CONFIG_PATH = DEFAULT_APP_DIR / '.env'
DEFAULT_CONFIG = {
    "PORT": 8080,
    "PLAID_ENV": "sandbox",
    "PLAID_CLIENT_ID": None,
    "PLAID_SECRET": None,
    "PLAID_SANDBOX_REDIRECT_URI": None,
    "PLAID_API_VERSION": "2020-09-14",
}

DEFAULT_DATA = {
    "links": []
}


# load .env values into environment variables
# use fallback config path if necessary
env_path = find_dotenv()
if not env_path and DEFAULT_CONFIG_PATH.is_file():
    env_path = DEFAULT_CONFIG_PATH
load_dotenv(env_path)



def load_config() -> dict:
    config = copy.deepcopy(DEFAULT_CONFIG)
    for key in config:
        if (val := os.getenv(key)) is not None:
            config[key] = val
    return config

def __merge(source, destination):
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            __merge(value, node)
        else:
            destination[key] = value

    return destination


def load_json_file(config_path: Path, default_json: dict) -> dict:
    config = default_json.copy()
    if config_path.is_file():
        with open(config_path) as f:
            config = __merge(json.load(f), config)
    return config


def write_json_file(config_path: Path, content: dict):
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(content, indent=True, sort_keys=True))

def save_data(data: dict, path: Path = None):
    if not path:
        path = DEFAULT_APP_DIR / "data.json"
    write_json_file(path, data)


def load_data(path: Path = None) -> dict:
    if not path:
        path = DEFAULT_APP_DIR / "data.json"
    return load_json_file(path, DEFAULT_DATA)