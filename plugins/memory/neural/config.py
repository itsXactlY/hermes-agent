"""Neural Memory plugin config — reads from ~/.hermes/config.yaml."""
import yaml
from pathlib import Path


def get_config() -> dict:
    cfg_path = Path.home() / ".hermes" / "config.yaml"
    full = yaml.safe_load(open(cfg_path)) or {}
    neural = full.get("memory", {}).get("neural", {})
    return neural
