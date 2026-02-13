import yaml
import json
from pathlib import Path
from typing import Dict, Any


def get_default_config_path() -> str:
    """Get the default configuration file path"""
    # Check for config in current directory
    if Path("config.yaml").exists():
        return "config.yaml"
    elif Path("config.json").exists():
        return "config.json"
    
    # Check for config in user home directory
    home_config = Path.home() / ".remote_cmd" / "config.yaml"
    if home_config.exists():
        return str(home_config)
    
    return "config.yaml"


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from file"""
    path = Path(config_path)
    
    if not path.exists():
        return get_default_config()
    
    with open(path, "r", encoding="utf-8") as f:
        if path.suffix in [".yaml", ".yml"]:
            return yaml.safe_load(f) or {}
        elif path.suffix == ".json":
            return json.load(f)
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}")


def get_default_config() -> Dict[str, Any]:
    """Get default configuration"""
    return {
        "hosts_file": "hosts.json",
        "default_ssh_port": 22,
        "default_timeout": 30,
        "log_level": "INFO"
    }


def save_config(config: Dict[str, Any], config_path: str):
    """Save configuration to file"""
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        if path.suffix in [".yaml", ".yml"]:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        elif path.suffix == ".json":
            json.dump(config, f, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}")
