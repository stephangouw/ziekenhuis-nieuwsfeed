import os
import json
from pathlib import Path

# The path where config.json will live
CONFIG_PATH = Path(__file__).parent / "config.json"

def load_config():
    if not CONFIG_PATH.exists():
        return {"networks": {}}
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config_data):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)

CONFIG = load_config()
