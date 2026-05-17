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

from chrome_action import ensure_chrome_action, NOT_LOGGED_IN_NOTE


# Shadow the built-in print so every line in this module gets a HH:MM:SS prefix
# without having to touch dozens of print() call sites.
_real_print = print
def print(*args, **kwargs):  # noqa: A001 — intentional builtin shadow
    _real_print(f"[{datetime.now().strftime('%H:%M:%S')}]", *args, **kwargs)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(SCRIPT_DIR, "skills")
UPLOAD_SKILL_PATH = os.path.join(SKILLS_DIR, "tiktok", "download-video-and-share-to-tiktok.md")
UPLOAD_ORIGINAL_AUDIO_SKILL_PATH = os.path.join(
    SKILLS_DIR, "tiktok", "download-video-and-share-to-tiktok-original-audio.md")
SWITCH_ACCOUNT_SKILL_PATH = os.path.join(SKILLS_DIR, "tiktok", "switch-account.md")
FAVORITE_MUSIC_SKILL_PATH = os.path.join(SKILLS_DIR, "tiktok", "favorite-music.md")
KILL_APP_SKILL_PATH = os.path.join(SKILLS_DIR, "ios", "kill-app.md")
SWITCH_SCRIPT = os.path.join(SCRIPT_DIR, "switch_to_iphone_mirroring.applescript")
CLAUDE_MODEL = "claude-sonnet-4-6"  # supports tool-use and has good reasoning for multi-step skills


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
    api_url = f"{CONFIG['feishu_info_url']}/pending-upload"
    print(api_url)
    req = urllib.request.Request(api_url)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())

    results = []
    for group in data.get("results", []):
        for item in group.get("items", []):
            record_id = item.get("record_id", "")
            fields = item.get("fields", {})
            video_id = extract_text(fields.get("product_id", []))
            video_urls = extract_links(fields.get("ai_video_urls", []))
            title = extract_text(fields.get("video_title", []))
            upload_device = extract_text(fields.get("video_upload_device", []))
            post_account = extract_text(fields.get("post_account", []))
            music_url, music_name = extract_music_info(fields.get("music info", []))
            for url in video_urls:
                rewritten = rewrite_url(url, video_id)
                results.append({
                    "video_id": video_id,
                    "url": rewritten,
                    "title": title,
                    "record_id": record_id,
                    "upload_device": upload_device,
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


def _mirroring_running() -> bool:
    return subprocess.run(["pgrep", "-x", "iPhone Mirroring"],
                          capture_output=True).returncode == 0


def ensure_mirroring() -> bool:
    """Make sure the iPhone Mirroring app is running. If not, launch it and wait
    up to 10s for the process to appear. Returns True on success, False if it
    refused to come up (e.g. iPhone locked, mirroring not paired, OS denial)."""
    if _mirroring_running():
        return True
    print("  iPhone Mirroring not running; launching…")
    subprocess.run(["open", "-a", "iPhone Mirroring"], check=False)
    for _ in range(20):
        time.sleep(0.5)
        if _mirroring_running():
            return True
    return False


# Track currently connected iPhone Mirroring device
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
    """Switch TikTok account if needed, using the switch-account skill.

    Skipped entirely when `config.switch_account` is `false` — useful when the
    iPhone is already set to the right account manually and you want to avoid
    the extra LLM-driven verification (it's slow and occasionally flaky)."""
    global current_account
    if not CONFIG.get("switch_account", True):
        print(f"  Skipping switch-account (config.switch_account=false); "
              f"assuming iPhone TikTok is on '{post_account}'.")
        return
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


URL_HIJACK_GUARD_MARKER = "URL_AUTOCOMPLETE_HIJACK_GUARD:"
UPLOAD_POSTED_MARKER = "UPLOAD_VIDEO_POSTED:"
UPLOAD_ABORTED_MARKER = "UPLOAD_VIDEO_ABORTED:"


def upload_video(video_url: str, title: str, skill_path: str = UPLOAD_SKILL_PATH) -> str:
    """Call Claude Code CLI to execute the mirroir skill at `skill_path`.
    Defaults to the full upload skill; pass `UPLOAD_ORIGINAL_AUDIO_SKILL_PATH` for the
    fallback path used when product addition failed.

    Returns an EMPTY string on confirmed success (skill emitted `UPLOAD_VIDEO_POSTED:`).
    Returns a NON-EMPTY failure note when the skill aborted (`UPLOAD_VIDEO_ABORTED:` marker),
    hit the URL-hijack guard, or exited cleanly without confirming a post (silent abort).
    The caller uses an empty return to mark Feishu as posted; non-empty to write the note
    into the 备注 column with `post_time=N/A`."""
    with open(skill_path, "r") as f:
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

    posted_seen = False
    abort_reason = ""
    hijack_detected = False

    def _scan(text: str) -> None:
        nonlocal posted_seen, abort_reason, hijack_detected
        if UPLOAD_POSTED_MARKER in text:
            posted_seen = True
        if UPLOAD_ABORTED_MARKER in text and not abort_reason:
            # Capture text after the marker on the same line, trimmed
            idx = text.find(UPLOAD_ABORTED_MARKER) + len(UPLOAD_ABORTED_MARKER)
            tail = text[idx:].splitlines()[0].strip() if text[idx:].strip() else ""
            abort_reason = tail or "(no reason given)"
        if URL_HIJACK_GUARD_MARKER in text:
            hijack_detected = True

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
                    text = block["text"]
                    print(f"  {text}", flush=True)
                    _scan(text)
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
                        _scan(text)
        elif etype == "result":
            result = event.get("result", "")
            text = str(result)
            print(f"  Result: {text[:300]}", flush=True)
            _scan(text)

    proc.wait()

    # Priority: explicit ABORTED > URL hijack > posted > silent abort
    if abort_reason:
        return f"上传未完成：{abort_reason}"
    if hijack_detected:
        return ("上传未完成：iOS Chrome omnibox autocomplete 抢回车（大小写错乱），"
                "需清掉相关 Chrome 浏览历史后重试")
    if posted_seen:
        # Sub-process may exit 0 anyway, but we trust the marker as the source of truth.
        return ""
    # Subprocess exited cleanly OR with non-zero, but no completion marker — silent abort.
    if proc.returncode != 0:
        return f"上传未完成：claude -p 子进程异常退出 (exit={proc.returncode})"
    return ("上传未完成：skill 没有发出 UPLOAD_VIDEO_POSTED 标记（可能 LLM 中途停了或被 mirroir 报错挡住），"
            "视频未实际发布")


def main():
    videos = fetch_pending_videos()
    print(f"Found {len(videos)} pending video(s)\n")

    if not videos:
        return

    for i, video in enumerate(videos, 1):
        print(f"[{i}/{len(videos)}] {video['video_id']}: {video['title'][:50]} (device: {video['upload_device']}, account: {video['post_account']}, music: {video['music_name']})")
        if not ensure_mirroring():
            print(f"  iPhone Mirroring failed to launch; skipping video.", file=sys.stderr)
            try:
                update_feishu_record(video["record_id"], post_time="N/A", note="iphone mirror not open")
            except Exception as e:
                print(f"  Feishu update failed: {e}\n", file=sys.stderr)
            continue
        ensure_device(video["upload_device"])
        ensure_account(video["post_account"])
        chrome_note = ensure_chrome_action(video["post_account"], video["video_id"])
        if chrome_note == NOT_LOGGED_IN_NOTE:
            # Login state for this account is dead — fallback upload would post under the
            # wrong account context; better to skip and let the user re-login + retry.
            print(f"  Account '{video['post_account']}' is not logged in; skipping video.",
                  file=sys.stderr)
            try:
                update_feishu_record(video["record_id"], post_time="N/A", note=chrome_note)
            except Exception as e:
                print(f"  Feishu update failed: {e}\n", file=sys.stderr)
            continue
        if chrome_note:
            print(f"  Product add failed ({chrome_note}); falling back to "
                  f"original-audio upload (no product link).")
            upload_note = upload_video(video["url"], video["title"],
                                       skill_path=UPLOAD_ORIGINAL_AUDIO_SKILL_PATH)
            try:
                if not upload_note:
                    update_feishu_record(video["record_id"], note=chrome_note)
                    print(f"  Fallback upload done. 备注={chrome_note}\n")
                else:
                    update_feishu_record(video["record_id"], post_time="N/A",
                                         note=f"加品失败且原音回退也失败：{chrome_note}；{upload_note}")
                    print(f"  Fallback upload also failed; Feishu marked N/A. 备注={upload_note}\n",
                          file=sys.stderr)
            except Exception as e:
                print(f"  Feishu update failed: {e}\n", file=sys.stderr)
            continue
        ensure_music_favorited(video["music_url"])
        upload_note = upload_video(video["url"], video["title"])
        try:
            if not upload_note:
                update_feishu_record(video["record_id"])
                print(f"  Done! Feishu record updated.\n")
            else:
                update_feishu_record(video["record_id"], post_time="N/A", note=upload_note)
                print(f"  Upload not confirmed posted; Feishu marked N/A. 备注={upload_note}\n",
                      file=sys.stderr)
        except Exception as e:
            print(f"  Feishu update failed: {e}\n", file=sys.stderr)

    print("All videos uploaded.")


INTERVAL_SECONDS = 3600


def loop_forever():
    """Run main() in a loop, sleeping INTERVAL_SECONDS between iterations.
    Exceptions in a single iteration are caught and logged so the loop never dies."""
    while True:
        cycle_start = datetime.now()
        print(f"\n=== cycle start: {cycle_start:%Y-%m-%d %H:%M:%S} ===")
        try:
            main()
        except KeyboardInterrupt:
            print("\nInterrupted; exiting loop.")
            return
        except Exception as e:
            print(f"!! cycle crashed: {type(e).__name__}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        print(f"=== cycle end: {datetime.now():%Y-%m-%d %H:%M:%S} ===")
        print(f"=== sleeping {INTERVAL_SECONDS}s until next cycle ===\n", flush=True)
        try:
            time.sleep(INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("\nInterrupted during sleep; exiting loop.")
            return


if __name__ == "__main__":
    if "--once" in sys.argv:
        main()
    else:
        loop_forever()
