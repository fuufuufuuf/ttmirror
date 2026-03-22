#!/usr/bin/env python3
"""Fetch pending videos and upload each to TikTok via Claude Code + Mirroir."""

import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime

SKILL_NAME = "safari/download-video-and-share-to-tiktok"


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
            if isinstance(item, dict) and item.get("type") == "url" and item.get("link"):
                links.append(item["link"])
    return links


def fetch_pending_videos():
    api_url = f"{CONFIG['feishu_info_url']}/pending-upload?handle={CONFIG['device_list'][0]['original_handle']}"
    req = urllib.request.Request(api_url)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())

    results = []
    for item in data.get("items", []):
        record_id = item.get("record_id", "")
        fields = item.get("fields", {})
        video_id = extract_text(fields.get("product_id", []))
        video_urls = extract_links(fields.get("ai_video_urls", []))
        title = extract_text(fields.get("title", []))
        for url in video_urls:
            rewritten = rewrite_url(url, video_id)
            results.append({"video_id": video_id, "url": rewritten, "title": title, "record_id": record_id})
    return results


def update_feishu_record(record_id: str):
    """Update Feishu table after successful upload."""
    device = CONFIG["device_list"][0]
    url = f"{CONFIG['feishu_info_url']}/update-record?record_id={record_id}"
    payload = json.dumps({
        "video_upload_device": device["id"],
        "post_account": device["new_handle"],
        "post_time": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def upload_video(video_url: str, title: str) -> bool:
    """Call Claude Code CLI to execute the mirroir skill."""
    prompt = (
        f"Use the mirroir skill '{SKILL_NAME}' to download and upload a video to TikTok.\n"
        f"VIDEO_URL: {video_url}\n"
        f"VIDEO_TITLE: {title}\n\n"
        f"Call get_skill with name='{SKILL_NAME}' first to load the steps, "
        f"then execute them one by one using the mirroir MCP tools. "
        f"Replace ${{VIDEO_URL}} with the URL above and ${{VIDEO_TITLE:-}} with the title above."
    )
    proc = subprocess.Popen(
        ["claude", "-p", "--model", "claude-sonnet-4-6",
         "--verbose", "--output-format", "stream-json",
         "--allowedTools", "mcp__mirroir__*"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        cwd="/Users/haowang/ttmirror",
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
        print(f"[{i}/{len(videos)}] {video['video_id']}: {video['title'][:50]}")
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
