"""
Application configuration management.

This module handles persistent storage of admin settings like the similarity threshold.
"""

import json
from pathlib import Path
from datetime import datetime

CONFIG_DIR = Path(__file__).resolve().parent
CONFIG_FILE = CONFIG_DIR / "system_config.json"

# Default configuration
DEFAULT_CONFIG = {
    "similarity_threshold": 0.30,
    "last_updated": datetime.now().isoformat(),
    "updated_by": "system"
}

def ensure_config_exists():
    """Ensure the config file exists with default values."""
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)

def load_config():
    """Load configuration from disk."""
    ensure_config_exists()
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to disk."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def get_threshold():
    """Get the current similarity threshold."""
    config = load_config()
    return config.get("similarity_threshold", 0.30)

def set_threshold(threshold, updated_by="admin"):
    """Set the similarity threshold."""
    if threshold < 0.25 or threshold > 0.35:
        raise ValueError("Threshold must be between 0.25 and 0.35")

    config = load_config()
    config["similarity_threshold"] = threshold
    config["last_updated"] = datetime.now().isoformat()
    config["updated_by"] = updated_by

    if save_config(config):
        return config
    else:
        raise Exception("Failed to save configuration")

# Initialize config on module load
ensure_config_exists()
