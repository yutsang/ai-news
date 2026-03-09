#!/usr/bin/env python3
"""
Shared utility functions used across multiple scrapers and processors.
"""

import json
import re
import yaml
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.yml") -> dict:
    """Load and return the YAML configuration file."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_json_response(text: str) -> dict:
    """
    Parse a JSON string returned by an AI model.
    Strips markdown code fences (```json ... ```) if present before parsing.
    """
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        # Take the content inside the first fence block
        inner = parts[1]
        if inner.startswith("json"):
            inner = inner[4:]
        text = inner.strip()
    result = json.loads(text)
    if isinstance(result, list):
        result = result[0] if result else {}
    return result


def format_date_str(
    date_str: str,
    from_fmt: str = "%Y-%m-%d",
    to_fmt: str = "%d/%m/%Y",
) -> str:
    """
    Reformat a date string from one format to another.
    Returns the original string unchanged if parsing fails.
    """
    try:
        return datetime.strptime(date_str.strip(), from_fmt).strftime(to_fmt)
    except (ValueError, AttributeError):
        return date_str


def parse_hk_price(price_str: str) -> str:
    """
    Convert a Hong Kong price string (supporting 萬 / 億 suffixes) to a
    plain integer string denominated in HKD.

    Examples:
        "2000萬"  → "200000000"  (wait, 2000 * 10000 = 20,000,000)
        "2億"     → "200000000"
        "30,000,000" → "30000000"
    """
    price_str = price_str.replace("$", "").replace(",", "").strip()
    try:
        if "億" in price_str:
            num = float(re.sub(r"[^0-9.]", "", price_str))
            return str(int(num * 100_000_000))
        elif "萬" in price_str:
            num = float(re.sub(r"[^0-9.]", "", price_str))
            return str(int(num * 10_000))
        else:
            return str(int(float(price_str))) if price_str else price_str
    except (ValueError, TypeError):
        return price_str
