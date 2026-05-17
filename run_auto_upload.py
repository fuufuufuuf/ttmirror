#!/usr/bin/env python3
"""Hourly cron entry: run auto_upload.py with a flock-based concurrency guard.

Skip silently if another copy is already running. Kernel releases the lock on
process exit even if killed -9. Logs are appended to logs/auto_upload_YYYYMMDD.log.
"""
import fcntl
import os
import subprocess
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCK_FILE = "/tmp/auto_upload.lock"
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")

# launchd's PATH is minimal — make sure `claude`, homebrew, and nvm-managed
# `node`/`npx` resolve. The latter is needed for the chrome-devtools MCP server,
# which is spawned via `npx -y chrome-devtools-mcp@latest`.
os.environ["PATH"] = ":".join([
    "/Users/tikaitongku/.local/bin",
    "/Users/tikaitongku/.nvm/versions/node/v24.14.0/bin",
    "/opt/homebrew/bin",
    os.environ.get("PATH", "/usr/bin:/bin"),
])

os.makedirs(LOG_DIR, exist_ok=True)
log_path = os.path.join(LOG_DIR, f"auto_upload_{datetime.now():%Y%m%d}.log")

lock_fp = open(LOCK_FILE, "w")
try:
    fcntl.flock(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    with open(log_path, "a") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] skip: another instance is running\n")
    sys.exit(0)

with open(log_path, "a") as f:
    f.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] === start ===\n")
    f.flush()

    # Pre-flight: confirm claude CLI can authenticate from this launchd subprocess
    # context. Skip the entire run otherwise — better to leave videos pending for the
    # next hour than to mark them all N/A. Observed failure: launchd subprocess sees
    # "Not logged in" intermittently even though the keychain entry is valid in the
    # user's shell.
    preflight = subprocess.run(
        ["claude", "-p", "--model", "claude-haiku-4-5-20251001", "say ok"],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60,
    )
    combined = preflight.stdout + preflight.stderr
    if preflight.returncode != 0 or "Not logged in" in combined:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] preflight failed "
                f"(exit={preflight.returncode}): {combined.strip()[:300]}\n")
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] === end (skipped: claude auth) ===\n")
        sys.exit(0)

    proc = subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "auto_upload.py")],
        cwd=SCRIPT_DIR, stdout=f, stderr=subprocess.STDOUT,
    )
    f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] === end (exit={proc.returncode}) ===\n")

sys.exit(proc.returncode)
