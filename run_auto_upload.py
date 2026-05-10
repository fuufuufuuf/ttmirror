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

# cron's PATH is minimal — make sure `claude` and homebrew binaries resolve.
os.environ["PATH"] = ":".join([
    "/Users/tikaitongku/.local/bin",
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
    proc = subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "auto_upload.py")],
        cwd=SCRIPT_DIR, stdout=f, stderr=subprocess.STDOUT,
    )
    f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] === end (exit={proc.returncode}) ===\n")

sys.exit(proc.returncode)
