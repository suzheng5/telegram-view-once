from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from nullshield.html_render import format_money, render_template
from nullshield.paths import OUTPUT_DIR, templates_dir

PAGE_FILES = {
    "fund_trace": ("fund_trace.html", "资金追踪.html"),
    "fund_recovery_extra": ("fund_recovery_extra.html", "资金追回-额外暴露.html"),
    "firewall": ("firewall.html", "防火墙警告.html"),
    "firewall_intrusion": ("firewall_intrusion.html", "防火墙-入侵.html"),
    "withdrawal_alert": ("withdrawal_alert.html", "提款警告.html"),
    "micro_tx": ("micro_tx.html", "小额交易警告.html"),
}

PAGE_COPY_LABELS = {
    "fund_trace": "复制-资金追踪",
    "fund_recovery_extra": "复制-资金追回-额外",
    "firewall": "复制-防火墙警告",
    "firewall_intrusion": "复制-防火墙-入侵",
    "withdrawal_alert": "复制-提款警告",
    "micro_tx": "复制-小额交易警告",
}

PAGE_OPEN_LABELS = {
    "fund_trace": "打开-资金追踪",
    "fund_recovery_extra": "打开-资金追回-额外",
    "firewall": "打开-防火墙警告",
    "firewall_intrusion": "打开-防火墙-入侵",
    "withdrawal_alert": "打开-提款警告",
    "micro_tx": "打开-小额交易警告",
}


def _ensure_output_dir() -> Path:
    path = Path(OUTPUT_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _case_id() -> str:
    now = datetime.now()
    return f"CF-{now.year}-{secrets.token_hex(3)[:5].upper()}"


def _load_dossier_css() -> str:
    return (templates_dir() / "_dossier_styles.css").read_text(encoding="utf-8")


def _dossier_common_values() -> dict[str, str]:
    return {
        "DOSSIER_CSS": _load_dossier_css(),
        "GENERATED_AT": _now_stamp(),
        "SHA_SEAL": secrets.token_hex(8),
        "SESSION_ID": secrets.token_hex(6).upper(),
        "CASE_ID": _case_id(),
        "EVIDENCE_ID": f"EP-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}",
    }


def _merge_values(*parts: dict[str, str]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for part in parts:
        merged.update(part)
    return merged


def _parse_amount(value: str) -> float:
    return float(str(value).replace(",", "").strip() or 0)


def _parse_nonneg_int(value: str, default: int = 0) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return max(0, parsed)


def _format_hms(total_sec: int) -> str:
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    seconds = total_sec % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _hold_label(total_sec: int) -> str:
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    seconds = total_sec % 60
    return f"{hours}h {minutes:02d}m {seconds:02d}s"


def _resolve_prior_traced(extra_cfg: dict, fund_cfg: dict) -> float:
    prior = _parse_amount(extra_cfg.get("prior_traced", ""))
    if prior > 0:
        return prior
    return _parse_amount(fund_cfg.get("principal", "0")) + _parse_amount(
        fund_cfg.get("profit", "0")
    )


def _fund_trace_values(cfg: dict) -> dict[str, str]:
    principal = _parse_amount(cfg.get("principal", "0"))
    profit = _parse_amount(cfg.get("profit", "0"))
    total = principal + profit
    identity_key = "0x" + secrets.token_hex(8).upper()
    return {
        "IDENTITY_KEY": identity_key,
        "SETTLEMENT_HASH": hashlib.sha256(identity_key.encode()).hexdigest()[:16],
        "TOTAL_DISPLAY": format_money(total),
        "TOTAL_RAW": str(int(total)) if total == int(total) else str(total),
    }


def _fund_recovery_extra_values(extra_cfg: dict, fund_cfg: dict) -> dict[str, str]:
    prior = _resolve_prior_traced(extra_cfg, fund_cfg)
    additional = _parse_amount(extra_cfg.get("additional_found", "0"))
    identity_key = "0x" + secrets.token_hex(8).upper()
    return {
        "PRIOR_TRACED_DISPLAY": format_money(prior),
        "ADDITIONAL_DISPLAY": format_money(additional),
        "COMBINED_TOTAL_DISPLAY": format_money(prior + additional),
        "IDENTITY_KEY": identity_key,
        "SETTLEMENT_HASH": hashlib.sha256(identity_key.encode()).hexdigest()[:16],
    }


def _firewall_values(cfg: dict) -> dict[str, str]:
    return {
        "TX_REMAINING": str(cfg.get("tx_remaining", "2")).strip(),
        "BALANCE_THRESHOLD": format_money(cfg.get("balance_threshold", "35000")),
    }


def _firewall_intrusion_values(cfg: dict) -> dict[str, str]:
    hours = _parse_nonneg_int(cfg.get("hold_hours", "51"), 51)
    minutes = _parse_nonneg_int(cfg.get("hold_minutes", "14"), 14)
    seconds = _parse_nonneg_int(cfg.get("hold_seconds", "28"), 28)
    hold_seconds = hours * 3600 + minutes * 60 + seconds
    if hold_seconds <= 0:
        hold_seconds = 1
    expires = datetime.now() + timedelta(seconds=hold_seconds)
    return {
        "HOLD_SECONDS": str(hold_seconds),
        "HOLD_HMS": _format_hms(hold_seconds),
        "HOLD_LABEL": _hold_label(hold_seconds),
        "HOLD_EXPIRES": expires.strftime("%Y-%m-%d %H:%M:%S"),
    }


def build_page(page_key: str, config: dict) -> Path:
    if page_key not in PAGE_FILES:
        raise KeyError(f"Unknown page: {page_key}")
    template_name, output_name = PAGE_FILES[page_key]
    template_path = templates_dir() / template_name
    if not template_path.is_file():
        raise FileNotFoundError(f"Template not found: {template_path}")

    if page_key == "fund_trace":
        values = _merge_values(_dossier_common_values(), _fund_trace_values(config["fund_trace"]))
    elif page_key == "fund_recovery_extra":
        values = _merge_values(
            _dossier_common_values(),
            _fund_recovery_extra_values(config["fund_recovery_extra"], config["fund_trace"]),
        )
    elif page_key == "firewall":
        values = _merge_values(_dossier_common_values(), _firewall_values(config["firewall"]))
    elif page_key == "firewall_intrusion":
        values = _merge_values(
            _dossier_common_values(),
            _firewall_intrusion_values(config["firewall_intrusion"]),
        )
    else:
        values = _dossier_common_values()

    html = render_template(template_path, values)
    output_path = _ensure_output_dir() / output_name
    output_path.write_text(html, encoding="utf-8")
    return output_path


def build_all_pages(config: dict) -> dict[str, Path]:
    return {key: build_page(key, config) for key in PAGE_FILES}
