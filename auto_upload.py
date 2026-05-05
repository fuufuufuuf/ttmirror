#!/usr/bin/env python3
"""Fetch pending videos and upload each to TikTok via Claude Code + Mirroir."""

import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime

from chrome_action import ensure_chrome_action

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(SCRIPT_DIR, "skills")
UPLOAD_SKILL_PATH = os.path.join(SKILLS_DIR, "tiktok", "download-video-and-share-to-tiktok.md")
SWITCH_ACCOUNT_SKILL_PATH = os.path.join(SKILLS_DIR, "tiktok", "switch-account.md")
FAVORITE_MUSIC_SKILL_PATH = os.path.join(SKILLS_DIR, "tiktok", "favorite-music.md")
KILL_APP_SKILL_PATH = os.path.join(SKILLS_DIR, "ios", "kill-app.md")
CLAUDE_MODEL = "claude-sonnet-4-6"


def _load_kill_app_skill() -> str:
    with open(KILL_APP_SKILL_PATH, "r") as f:
        return f.read()


KILL_APP_SKILL = _load_kill_app_skill()


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
            if isinstance(item, dict) and item.get("type") in ("text", "url") and item.get("text", "").strip():
                return item["text"].strip()
    return ""


def extract_music_info(field):
    """Parse music info JSON from a Feishu text field. Returns (url, title) or (None, None)."""
    raw = extract_text(field)
    if not raw:
        return None, None
    try:
        info = json.loads(raw)
    except json.JSONDecodeError:
        return None, None
    return info.get("url"), info.get("title")


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
        post_account = extract_text(fields.get("post_account", []))
        music_url, music_name = extract_music_info(fields.get("music info", []))
        for url in video_urls:
            rewritten = rewrite_url(url, video_id)
            results.append({
                "video_id": video_id,
                "url": rewritten,
                "title": title,
                "record_id": record_id,
                "post_account": post_account,
                "music_url": music_url,
                "music_name": music_name,
            })
    return results


def update_feishu_record(record_id: str, post_time: str = "", note: str = ""):
    """Update Feishu table. If post_time is empty, use the current timestamp.
    If note is non-empty, also write it to the 备注 column (added to the table for skipped/failed runs)."""
    url = f"{CONFIG['feishu_info_url']}/update-record?record_id={record_id}"
    body = {"post_time": post_time or datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
    if note:
        body["备注"] = note
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


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
        f"Whenever a step requires force-quitting / killing / restarting an iPhone app, "
        f"follow the SUPPORT SKILL: kill-app procedure below — never swipe in App Switcher manually.\n\n"
        f"--- SKILL ---\n{skill_content}\n--- END SKILL ---\n\n"
        f"--- SUPPORT SKILL: kill-app ---\n{KILL_APP_SKILL}\n--- END SUPPORT SKILL ---"
    )
    proc = subprocess.Popen(
        ["claude", "-p", "--model", CLAUDE_MODEL,
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


current_music_url = None


def ensure_music_favorited(music_url: str):
    """Run the favorite-music skill once per unique music URL to ensure it's saved."""
    global current_music_url
    if not music_url:
        return
    if current_music_url == music_url:
        print(f"  Music already favorited this run: {music_url}")
        return
    print(f"  Favoriting music: {music_url}")
    with open(FAVORITE_MUSIC_SKILL_PATH, "r") as f:
        skill_content = f.read()
    prompt = (
        f"Favorite a TikTok music following the skill steps below.\n"
        f"MUSIC_URL: {music_url}\n\n"
        f"Execute the steps one by one using the mirroir MCP tools. "
        f"Replace ${{MUSIC_URL}} with the URL above.\n\n"
        f"Whenever a step requires force-quitting / killing / restarting an iPhone app, "
        f"follow the SUPPORT SKILL: kill-app procedure below — never swipe in App Switcher manually.\n\n"
        f"--- SKILL ---\n{skill_content}\n--- END SKILL ---\n\n"
        f"--- SUPPORT SKILL: kill-app ---\n{KILL_APP_SKILL}\n--- END SUPPORT SKILL ---"
    )
    proc = subprocess.Popen(
        ["claude", "-p", "--model", CLAUDE_MODEL,
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
        current_music_url = music_url
        print(f"  Music favorited.")
    else:
        print(f"  Warning: favorite-music may have failed (exit {proc.returncode})", file=sys.stderr)


def upload_video(video_url: str, title: str) -> bool:
    """Call Claude Code CLI to execute the mirroir skill."""
    with open(UPLOAD_SKILL_PATH, "r") as f:
        skill_content = f.read()
    prompt = (
        f"Download and upload a video to TikTok following the skill steps below.\n"
        f"VIDEO_URL: {video_url}\n"
        f"VIDEO_TITLE: {title}\n\n"
        f"Execute the steps one by one using the mirroir MCP tools. "
        f"Replace ${{VIDEO_URL}} with the URL above and ${{VIDEO_TITLE}} with the title above.\n\n"
        f"Whenever a step requires force-quitting / killing / restarting an iPhone app, "
        f"follow the SUPPORT SKILL: kill-app procedure below — never swipe in App Switcher manually.\n\n"
        f"--- SKILL ---\n{skill_content}\n--- END SKILL ---\n\n"
        f"--- SUPPORT SKILL: kill-app ---\n{KILL_APP_SKILL}\n--- END SUPPORT SKILL ---"
    )
    proc = subprocess.Popen(
        ["claude", "-p", "--model", CLAUDE_MODEL,
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
        print(f"[{i}/{len(videos)}] {video['video_id']}: {video['title'][:50]} (account: {video['post_account']}, music: {video['music_name']})")
        ensure_account(video["post_account"])
        chrome_note = ensure_chrome_action(video["post_account"], video["video_id"])
        if chrome_note:
            print(f"  Skipping upload: {chrome_note}")
            try:
                update_feishu_record(video["record_id"], post_time="N/A", note=chrome_note)
                print(f"  Feishu record marked: post_time=N/A, 备注={chrome_note}\n")
            except Exception as e:
                print(f"  Feishu update failed: {e}\n", file=sys.stderr)
            continue
        ensure_music_favorited(video["music_url"])
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
