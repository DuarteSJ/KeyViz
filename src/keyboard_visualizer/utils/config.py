import json
from pathlib import Path
from typing import Dict, Any

def get_default_config_path() -> Path:
    """Get the path to the default configuration file bundled with the app."""
    path = Path(__file__).parent.parent.parent.parent/ "config/default.json"
    print(f"Default config path: {path}")
    return path

def get_user_config_path() -> Path:
    """Get the path to the user's configuration file."""
    return Path.home() / ".config" / "KeyViz" / "config.json"

def load_default_config() -> Dict[str, Any]:
    """Load the default configuration bundled with the app."""
    default_config_path = get_default_config_path()
    try:
        with open(default_config_path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load default config: {e}")
        exit(1)

def load_user_config() -> Dict[str, Any]:
    """Load the user's configuration file."""
    user_config_path = get_user_config_path()
    try:
        with open(user_config_path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def merge_configs(default_config: Dict[str, Any], user_config: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge user config into default config."""
    merged = default_config.copy()
    
    for key, value in user_config.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            merged[key] = merge_configs(merged[key], value)
        else:
            # Override with user value
            merged[key] = value
    
    return merged

def load_config() -> Dict[str, Any]:
    """Load the complete configuration (default + user overrides)."""
    default_config = load_default_config()
    user_config = load_user_config()
    
    return merge_configs(default_config, user_config)

def load_key_colors() -> Dict[str, str]:
    """Load key colors from configuration."""
    config = load_config()
    colors = config.get("key_colors", {})
    print(f"Loaded key colors: {colors}\n")
    return colors

def load_main_window_settings() -> Dict[str, str]:
    """Load main window colors from configuration."""
    config = load_config()
    settings = config.get("main_window", {})
    print(f"Loaded main window settings colors: {settings}\n")
    return settings

def load_dialog_colors() -> Dict[str, str]:
    """Load dialog colors from configuration."""
    config = load_config()
    colors = config.get("dialog_colors", {})
    print(f"Loaded dialog colors: {colors}\n")
    return colors

def create_default_user_config():
    """Create a default user config file based on the app defaults."""
    user_config_path = get_user_config_path()
    
    # Create directory if it doesn't exist
    user_config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Copy default config as starting point for user
    default_config = load_default_config()
    
    with open(user_config_path, "w") as f:
        json.dump(default_config, f, indent=2)
    
    print(f"Created default user configuration at: {user_config_path}")

def save_user_config(config: Dict[str, Any]):
    """Save user configuration to file."""
    user_config_path = get_user_config_path()
    user_config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(user_config_path, "w") as f:
        json.dump(config, f, indent=2)
