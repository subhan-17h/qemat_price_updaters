#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import smtplib
import socket
import subprocess
import time
from email.message import EmailMessage
from pathlib import Path


SUPPRESSION_SECONDS = 24 * 60 * 60


def safe_unit_name(unit: str) -> str:
    return "".join(char if char.isalnum() or char in "-_." else "_" for char in unit)


def state_path(unit: str) -> Path:
    state_dir = Path(os.getenv("QEMAT_ALERT_STATE_DIR", "/var/lib/qemat-alerts"))
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / f"{safe_unit_name(unit)}.json"


def mark_success(unit: str) -> None:
    path = state_path(unit)
    if path.exists():
        path.unlink()


def recent_journal(unit: str) -> str:
    result = subprocess.run(
        ["journalctl", "-u", unit, "-n", "120", "--no-pager", "--output=short-iso"],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    output = result.stdout.strip() or result.stderr.strip()
    return output[-20000:] if output else "No journal output was available."


def send_failure(unit: str) -> bool:
    path = state_path(unit)
    now = time.time()
    if path.exists():
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
            if now - float(previous.get("last_sent", 0)) < SUPPRESSION_SECONDS:
                print(f"Duplicate alert for {unit} suppressed for 24 hours")
                return False
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass

    username = os.environ["SMTP_USERNAME"]
    password = os.environ["SMTP_APP_PASSWORD"]
    recipient = os.getenv("ALERT_TO", username)
    host = socket.gethostname()
    journal = recent_journal(unit)

    message = EmailMessage()
    message["Subject"] = f"[Qemat] Service failed: {unit} on {host}"
    message["From"] = username
    message["To"] = recipient
    message.set_content(
        f"Qemat automation failure\n\n"
        f"Service: {unit}\n"
        f"Host: {host}\n"
        f"Unix timestamp: {int(now)}\n"
        f"State: failed\n\n"
        f"Recent journal output:\n{journal}\n"
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(username, password)
        smtp.send_message(message)

    path.write_text(json.dumps({"last_sent": now}), encoding="utf-8")
    print(f"Failure alert sent for {unit} to {recipient}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Send rate-limited Qemat systemd failure alerts")
    parser.add_argument("event", choices=["failure", "success"])
    parser.add_argument("unit")
    args = parser.parse_args()

    if args.event == "success":
        mark_success(args.unit)
    else:
        send_failure(args.unit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
