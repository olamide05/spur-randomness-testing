import json
from pathlib import Path

def load_config(config_path):
    with open(Path(config_path), 'r') as f:
        return json.load(f)

config = load_config("src/automation/config/default_config.json")
print(config)
print(config['mode'])  # Access a specific setting from the config