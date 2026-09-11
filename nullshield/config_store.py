from __future__ import annotations

import json
from copy import deepcopy

from nullshield.paths import CONFIG_FILE

DEFAULT_CONFIG = {
    "fund_trace": {
        "principal": "8000",
        "profit": "2000",
    },
    "fund_recovery_extra": {
        "prior_traced": "",
        "additional_found": "315700",
    },
    "firewall": {
        "tx_remaining": "2",
        "balance_threshold": "35000",
    },
    "firewall_intrusion": {
        "hold_hours": "51",
        "hold_minutes": "14",
        "hold_seconds": "28",
    },
}


def _merge(default: dict, loaded: dict) -> dict:
    result = deepcopy(default)
    for key, value in loaded.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key].update(value)
        elif key in result:
            result[key] = value
    return result


def load_config() -> dict:
    if not CONFIG_FILE.is_file():
        return deepcopy(DEFAULT_CONFIG)
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return _merge(DEFAULT_CONFIG, data)
    except (json.JSONDecodeError, OSError):
        return deepcopy(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
