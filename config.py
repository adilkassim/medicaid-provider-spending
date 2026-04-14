"""
Shared configuration utility for the Medicaid Provider Spending dashboard.
Reads/writes .medicaid_config.json at the project root.
"""

import json
import os
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / ".medicaid_config.json"

DEFAULTS: dict = {
    "parquet_path": os.path.expanduser("~/Downloads/medicaid-provider-spending.parquet"),
    "nppes_csv_path": os.path.expanduser("~/Downloads/npidata.csv"),
    "hcpcs_csv_path": "",
    "exports_dir": str(Path(__file__).parent / "exports"),
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                saved = json.load(f)
            return {**DEFAULTS, **saved}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULTS)


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
