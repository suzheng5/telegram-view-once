from __future__ import annotations

import re
from pathlib import Path


def render_template(template_path: Path, values: dict[str, str]) -> str:
    content = template_path.read_text(encoding="utf-8")
    for key in sorted(values, key=len, reverse=True):
        content = content.replace(f"@@{key}@@", str(values[key]))
    leftover = sorted(set(re.findall(r"@@\w+@@", content)))
    if leftover:
        raise ValueError(f"Unreplaced placeholders in {template_path.name}: {leftover}")
    return content


def format_money(value: str | int | float, prefix: str = "$") -> str:
    number = float(str(value).replace(",", "").strip() or 0)
    return f"{prefix}{number:,.0f}"
