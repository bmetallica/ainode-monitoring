import os
import json
from pathlib import Path

CONFIG_PATH = Path("/app/data/mqtt_config.json")
DEFAULT_CONFIG = {
    "broker": "",
    "port": 1883,
    "user": "",
    "password": "",
    "topic_prefix": "",
    "connected": False
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                saved = json.load(f)
            cfg = {**DEFAULT_CONFIG, **saved}
        except (json.JSONDecodeError, IOError):
            cfg = DEFAULT_CONFIG.copy()
    else:
        cfg = DEFAULT_CONFIG.copy()
    cfg["port"] = int(cfg.get("port", 1883))
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
