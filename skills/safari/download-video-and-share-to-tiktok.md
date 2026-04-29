---
version: 1
name: Download Video and Share to TikTok
app: Chrome
ios_min: "17.0"
locale: "en_US"
tags: ["chrome", "download", "video", "tiktok", "share", "upload"]
---

Download a video from a URL in Chrome and share it directly to TikTok for posting.

## Rules

- **Coordinates**: **MUST** use `describe_screen` to get tap coordinates — never estimate from screenshot pixels. `describe_screen` returns coordinates that can be used directly with `tap`. `screenshot` is only for visual verification, not for locating tap targets.
- **Pacing**: Wait **2 seconds** (`sleep 2`) between consecutive mirroir tool calls to avoid rate limits. Only use `describe_screen` when you need to find a tap target.

- **Fixed coordinates**:
  - **Profile** tab: **(300, 680)**
  - **Next** button: **(248, 680)**
  - **Post** button: **(248, 680)**
- **Keyboard shortcuts** (iPhone Mirroring):
  - **Cmd+1**: Home Screen
  - **Cmd+2**: App Switcher
  - **Cmd+3**: Spotlight Search

## Steps

### Part 1: Open Chrome and navigate to video URL

1. Press **Cmd+1** to go to the Home Screen
2. Press **Cmd+3** to open Spotlight Search
3. Type "chrome" and press **Return** to launch chrome
4. Wait for chrome to appear
5. Open a new tab with **Cmd+T**
6. Press **Cmd+L** to focus the address bar
7. Copy the URL to macOS clipboard: run `echo -n "${VIDEO_URL}" | pbcopy`
8. Paste with **Cmd+V**
9. Press **Return**

### Part 2: Share video to TikTok

10. After pressing Return on the URL, a download bar appears at the bottom of the page showing the file name (e.g. `1731837266182378409.mp4`), file size, source URL, and a blue **DOWNLOAD** button on the right.
    - **Verify**: extract the numeric ID from `${VIDEO_URL}` (the digit segment before `.mp4`) and confirm it matches the file name shown in the bottom bar. If they do not match, the wrong page loaded — reload and retry.
    - **You MUST tap the "DOWNLOAD" button.** The download does NOT start automatically just from loading the page; only tapping DOWNLOAD triggers it.
    - Use `describe_screen` to locate the DOWNLOAD element.
    - After tapping, wait for the "Download complete" banner to appear at the bottom of the screen. If it does not appear within 5 seconds, reload the page and retry.
11. Tap "OPEN IN..." on the download complete banner to open the share sheet
12. Wait for the share sheet to appear
13. Use `describe_screen` to find the app icon row (the row containing AirDrop / Mail / etc.) and check if "TikTok" is present. If not visible, swipe **right** on that row to reveal more apps: take the Y coordinate of any visible app icon in that row from `describe_screen`, then call `swipe(from_x=50, to_x=200, from_y=<that Y>, to_y=<that Y>, duration_ms=500)`. After the swipe, `describe_screen` again. Repeat until "TikTok" appears, then tap it.
14. Wait for TikTok to open. A "Share on TikTok" modal appears with **Video** and **Message** buttons. Use `describe_screen` to locate the "Video" button, then tap it to enter the video editing flow.
15. If "iPhone camera is not available from Mac" dialog appears, dismiss it by running `dismiss_camera_dialog.sh` or using cliclick to click OK at the dialog's screen position

### Part 3: Edit and post on TikTok

16. Tap "Add sound" at the top center of the editing screen
17. Wait for the sound picker to appear
18. Tap "Original" to mute the original video audio
19. Tap "For you" tab to browse recommended music
20. Swipe up to scroll down the music list
21. Tap a random music track to select it
22. Tap fixed coordinates **(150, 200)** to return to the video editor
23. **DO NOT use `describe_screen`**. Tap **Next** directly at fixed coordinates **(248, 680)**. The OCR returns incorrect Y for this button.
24. Wait for the post editing screen (caption, hashtags)
25. Tap the "Add description..." text field, then use `type_text` to enter the video title. Copy the title to macOS clipboard first: run `echo -n "${VIDEO_TITLE:-}" | pbcopy`, then paste with **Cmd+V**.
26. **DO NOT use `describe_screen`**. Tap **Post** directly at fixed coordinates **(248, 680)**. The OCR returns incorrect Y for this button.
27. Wait for upload to complete
28. Screenshot: "tiktok_posted"
