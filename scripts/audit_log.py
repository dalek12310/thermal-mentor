"""L8 — Append-only JSONL audit log."""
from __future__ import annotations

import datetime as dt
import json
import secrets
import string
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]  # scripts/ -> repo root
LOG_DIR = _REPO_ROOT / "audit_log"
_ALPHABET = string.ascii_letters + string.digits


def new_id() -> str:
    """e.g. 20260523-153012-abc123."""
    now = dt.datetime.now()
    suffix = "".join(secrets.choice(_ALPHABET) for _ in range(6))
    return f"{now.strftime('%Y%m%d-%H%M%S')}-{suffix}"


def _month_path(yyyy_mm: str) -> Path:
    return LOG_DIR / f"{yyyy_mm}.jsonl"


def _current_month() -> str:
    return dt.date.today().strftime("%Y-%m")


def append(record: dict[str, Any]) -> str:
    """Append one JSON record to current month's log. Return audit_log_id."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    aid = record.get("audit_log_id") or new_id()
    record["audit_log_id"] = aid
    record.setdefault("timestamp", dt.datetime.now().isoformat(timespec="seconds"))
    path = _month_path(_current_month())
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return aid


def read_month(yyyy_mm: str) -> list[dict[str, Any]]:
    path = _month_path(yyyy_mm)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def append_user_correction(yyyy_mm: str, audit_log_id: str, correction: dict) -> bool:
    """Add `user_correction` to a specific record by rewriting the file."""
    runs = read_month(yyyy_mm)
    found = False
    for r in runs:
        if r["audit_log_id"] == audit_log_id:
            r["user_correction"] = correction
            found = True
    if not found:
        return False
    path = _month_path(yyyy_mm)
    with path.open("w", encoding="utf-8") as f:
        for r in runs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return True
