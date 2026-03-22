#!/usr/bin/env python3
"""Test: fetch the first pending video and update its Feishu record."""

from auto_upload import fetch_pending_videos, update_feishu_record

videos = fetch_pending_videos()
if not videos:
    print("No pending videos found.")
else:
    video = videos[0]
    print(f"Updating record for: {video['video_id']} - {video['title'][:50]}")
    print(f"  record_id: {video['record_id']}")
    result = update_feishu_record(video["record_id"])
    print(f"  Response: {result}")
