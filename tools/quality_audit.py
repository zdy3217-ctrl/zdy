#!/usr/bin/env python3
"""Non-intrusive quality audit for NarratorAI Omega deliverable."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "cmd.exe"
REPORT_DIR = ROOT / "reports"
REPORT_FILE = REPORT_DIR / "quality_audit.json"


@dataclass
class CheckResult:
    name: str
    status: str
    details: str


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_check(name: str, func) -> CheckResult:
    try:
        return CheckResult(name=name, status="pass", details=func())
    except Exception as exc:  # noqa: BLE001 - keep full failure visibility
        return CheckResult(name=name, status="fail", details=str(exc))


def check_binary_exists() -> str:
    if not BINARY.exists():
        raise FileNotFoundError(f"missing file: {BINARY}")
    if not BINARY.is_file():
        raise ValueError(f"not a regular file: {BINARY}")
    return "binary exists"


def check_pe_signature() -> str:
    data = BINARY.read_bytes()[:2]
    if data != b"MZ":
        raise ValueError("invalid PE signature; expected MZ")
    return "PE header signature is MZ"


def check_binary_size() -> str:
    size = BINARY.stat().st_size
    if size <= 0:
        raise ValueError("binary size is 0")
    return f"size={size} bytes"


def check_sha256() -> str:
    digest = sha256sum(BINARY)
    return f"sha256={digest}"


def check_wine_availability() -> str:
    wine = shutil.which("wine")
    if wine is None:
        return "wine not found (expected on Linux if running .exe directly)"
    return f"wine found at {wine}"


def check_git_clean_hint() -> str:
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git status failed")
    changed = proc.stdout.strip().splitlines()
    return "working tree clean" if not changed else f"working tree has {len(changed)} changed item(s)"


def main() -> int:
    checks = [
        run_check("binary_exists", check_binary_exists),
        run_check("pe_signature", check_pe_signature),
        run_check("binary_size", check_binary_size),
        run_check("sha256", check_sha256),
        run_check("wine_availability", check_wine_availability),
        run_check("git_status_hint", check_git_clean_hint),
    ]

    passed = sum(1 for c in checks if c.status == "pass")
    failed = sum(1 for c in checks if c.status == "fail")

    payload = {
        "project": "NarratorAI Omega",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "platform": {
            "python": sys.version,
            "os": os.name,
            "sys_platform": sys.platform,
        },
        "summary": {
            "total": len(checks),
            "passed": passed,
            "failed": failed,
        },
        "checks": [asdict(c) for c in checks],
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Audit written to: {REPORT_FILE}")
    for c in checks:
        print(f"[{c.status.upper()}] {c.name}: {c.details}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
