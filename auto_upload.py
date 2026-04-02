#!/usr/bin/env python3
"""Fetch pending videos and upload each to TikTok via Claude Code + Mirroir."""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(SCRIPT_DIR, "skills")
UPLOAD_SKILL_PATH = os.path.join(SKILLS_DIR, "safari", "download-video-and-share-to-tiktok.md")
SWITCH_ACCOUNT_SKILL_PATH = os.path.join(SKILLS_DIR, "tiktok", "switch-account.md")
SWITCH_SCRIPT = os.path.join(SCRIPT_DIR, "switch_to_iphone_mirroring.applescript")


def load_config():
    with open("config.json", "r") as f:
        return json.load(f)


CONFIG = load_config()


def rewrite_url(url: str, video_id: str) -> str:
    pattern = r"(https://res\.cloudinary\.com/[^/]+/[^/]+/[^/]+)/(.*)"
    match = re.match(pattern, url)
    if not match:
        return url
    return f"{match.group(1)}/fl_attachment:{video_id}/{match.group(2)}"


def extract_text(field):
    if isinstance(field, list):
        for item in field:
            if isinstance(item, dict) and item.get("type") == "text" and item.get("text", "").strip():
                return item["text"].strip()
    return ""


def extract_links(field):
    links = []
    if isinstance(field, list):
        for item in field:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "url" and item.get("link"):
                links.append(item["link"])
            elif item.get("type") == "text" and item.get("text", "").startswith("http"):
                links.append(item["text"])
    return links


def fetch_pending_videos():
    api_url = f"{CONFIG['feishu_info_url']}/pending-upload?handle={CONFIG['handle']}"
    print(api_url)
    req = urllib.request.Request(api_url)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())

    results = []
    for item in data.get("items", []):
        record_id = item.get("record_id", "")
        fields = item.get("fields", {})
        video_id = extract_text(fields.get("product_id", []))
        video_urls = extract_links(fields.get("ai_video_urls", []))
        title = extract_text(fields.get("video_title", []))
        upload_device = extract_text(fields.get("video_upload_device", []))
        post_account = extract_text(fields.get("post_account", []))
        for url in video_urls:
            rewritten = rewrite_url(url, video_id)
            results.append({
                "video_id": video_id,
                "url": rewritten,
                "title": title,
                "record_id": record_id,
                "upload_device": upload_device,
                "post_account": post_account,
            })
    return results


def update_feishu_record(record_id: str):
    """Update Feishu table after successful upload."""
    url = f"{CONFIG['feishu_info_url']}/update-record?record_id={record_id}"
    payload = json.dumps({
        "post_time": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


# Track currently connected device
current_device = None


def ensure_device(upload_device: str):
    """Switch iPhone Mirroring to the target device if needed."""
    global current_device
    if not upload_device:
        return
    # Normalize: "iphone 287" -> "iPhone 287" (match System Settings menu item)
    target = upload_device.strip()
    if target.lower().startswith("iphone"):
        target = "iPhone" + target[6:]
    if current_device and current_device.lower() == target.lower():
        print(f"  Device already connected: {current_device}")
        return
    print(f"  Switching device: {current_device} -> {target}")
    proc = subprocess.run(
        ["osascript", SWITCH_SCRIPT, target],
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        print(f"  Warning: switch script exited {proc.returncode}: {proc.stderr}", file=sys.stderr)
    # Wait for connection to establish
    time.sleep(10)
    current_device = target
    print(f"  Device switched to: {target}")


# Track currently active TikTok account
current_account = None


def ensure_account(post_account: str):
    """Switch TikTok account if needed, using the switch-account skill."""
    global current_account
    if not post_account:
        return
    target = post_account.strip()
    if current_account and current_account.lower() == target.lower():
        print(f"  Account already active: {current_account}")
        return
    print(f"  Switching TikTok account: {current_account} -> {target}")
    with open(SWITCH_ACCOUNT_SKILL_PATH, "r") as f:
        skill_content = f.read()
    prompt = (
        f"Switch the TikTok account to '{target}' following the skill steps below.\n"
        f"ACCOUNT_USERNAME: {target}\n\n"
        f"Execute the steps one by one using the mirroir MCP tools. "
        f"Replace ${{ACCOUNT_USERNAME}} with the username above.\n\n"
        f"--- SKILL ---\n{skill_content}\n--- END SKILL ---"
    )
    proc = subprocess.Popen(
        ["claude", "-p", "--model", "claude-haiku-4-5-20251001",
         "--verbose", "--output-format", "stream-json",
         "--allowedTools", "mcp__mirroir__*", "Bash"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        cwd=SCRIPT_DIR,
        text=True,
        bufsize=1,
    )
    proc.stdin.write(prompt)
    proc.stdin.close()

    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        etype = event.get("type")
        if etype == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "text" and block.get("text"):
                    print(f"  {block['text']}", flush=True)
                elif block.get("type") == "tool_use":
                    name = block.get("name", "")
                    inp = json.dumps(block.get("input", {}), ensure_ascii=False)
                    print(f"  -> {name}({inp})", flush=True)
        elif etype == "tool_result":
            content = event.get("content", "")
            if isinstance(content, list):
                for c in content:
                    if c.get("type") == "text":
                        print(f"     = {c.get('text', '')[:200]}", flush=True)
        elif etype == "result":
            print(f"  Result: {str(event.get('result', ''))[:300]}", flush=True)

    proc.wait()
    if proc.returncode == 0:
        current_account = target
        print(f"  Account switched to: {target}")
    else:
        print(f"  Warning: account switch may have failed (exit {proc.returncode})", file=sys.stderr)


def upload_video(video_url: str, title: str) -> bool:
    """Call Claude Code CLI to execute the mirroir skill."""
    with open(UPLOAD_SKILL_PATH, "r") as f:
        skill_content = f.read()
    prompt = (
        f"Download and upload a video to TikTok following the skill steps below.\n"
        f"VIDEO_URL: {video_url}\n"
        f"VIDEO_TITLE: {title}\n\n"
        f"Execute the steps one by one using the mirroir MCP tools. "
        f"Replace ${{VIDEO_URL}} with the URL above and ${{VIDEO_TITLE:-}} with the title above.\n\n"
        f"--- SKILL ---\n{skill_content}\n--- END SKILL ---"
    )
    proc = subprocess.Popen(
        ["claude", "-p", "--model", "claude-haiku-4-5-20251001",
         "--verbose", "--output-format", "stream-json",
         "--allowedTools", "mcp__mirroir__*", "Bash"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        cwd=SCRIPT_DIR,
        text=True,
        bufsize=1,
    )
    proc.stdin.write(prompt)
    proc.stdin.close()

    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        etype = event.get("type")
        if etype == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "text" and block.get("text"):
                    print(f"  {block['text']}", flush=True)
                elif block.get("type") == "tool_use":
                    name = block.get("name", "")
                    inp = json.dumps(block.get("input", {}), ensure_ascii=False)
                    print(f"  -> {name}({inp})", flush=True)
        elif etype == "tool_result":
            content = event.get("content", "")
            if isinstance(content, list):
                for c in content:
                    if c.get("type") == "text":
                        text = c.get("text", "")
                        print(f"     = {text[:200]}", flush=True)
        elif etype == "result":
            result = event.get("result", "")
            print(f"  Result: {str(result)[:300]}", flush=True)

    proc.wait()
    return proc.returncode == 0


def main():
    videos = fetch_pending_videos()
    print(f"Found {len(videos)} pending video(s)\n")

    if not videos:
        return

    for i, video in enumerate(videos, 1):
        print(f"[{i}/{len(videos)}] {video['video_id']}: {video['title'][:50]} (device: {video['upload_device']}, account: {video['post_account']})")
        ensure_device(video["upload_device"])
        ensure_account(video["post_account"])
        success = upload_video(video["url"], video["title"])
        if success:
            try:
                update_feishu_record(video["record_id"])
                print(f"  Done! Feishu record updated.\n")
            except Exception as e:
                print(f"  Upload done but Feishu update failed: {e}\n", file=sys.stderr)
        else:
            print(f"  Failed! Stopping.\n", file=sys.stderr)
            sys.exit(1)

    print("All videos uploaded.")


if __name__ == "__main__":
    main()
