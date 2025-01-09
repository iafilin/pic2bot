import json
import os

CONFIG_FILE = "config.json"

def load_config():
    """Загружает настройки из файла."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(config):
    """Сохраняет настройки в файл."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)
