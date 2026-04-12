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
- **Failure recovery**: If any step fails or the UI is not in the expected state, **do NOT try alternative approaches, workarounds, or ad-hoc recovery**. Immediately kill **both Chrome and TikTok** (force-quit via App Switcher) and restart the entire skill from **Step 1**.

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

10. Tap "DOWNLOAD". Wait for the "Download complete" banner to appear at the bottom of the screen
11. Tap "OPEN IN..." on the download complete banner to open the share sheet
12. Wait for the share sheet to appear
13. Use `describe_screen` to check if "TikTok" is in the app icon row. If not visible, swipe right (from_x=200, to_x=50, duration 1000ms) on the app row to reveal more apps, then `describe_screen` again. Repeat until "TikTok" appears, then tap it.
14. Wait for TikTok to open. A "Share on TikTok" modal appears with **Video** and **Message** buttons. Use `describe_screen` to locate the "Video" button, then tap it to enter the video editing flow.
15. If "iPhone camera is not available from Mac" dialog appears, dismiss it by running `dismiss_camera_dialog.sh` or using cliclick to click OK at the dialog's screen position

### Part 3: Edit and post on TikTok

16. Tap "Add sound" at the top center of the editing screen
17. Wait for the sound picker to appear
18. Tap "Original" to mute the original video audio
19. Tap "For you" tab to browse recommended music
20. Tap the upper-center area of the screen to return to the video editor
21. **DO NOT use `describe_screen`**. Tap **Next** directly at fixed coordinates **(248, 680)**. The OCR returns incorrect Y for this button.
22. Wait for the post editing screen (caption, hashtags)
23. Tap the "Add description..." text field, then use `type_text` to enter the video title. Copy the title to macOS clipboard first: run `echo -n "${VIDEO_TITLE:-}" | pbcopy`, then paste with **Cmd+V**.
24. **DO NOT use `describe_screen`**. Tap **Post** directly at fixed coordinates **(248, 680)**. The OCR returns incorrect Y for this button.
25. Wait for upload to complete
26. Screenshot: "tiktok_posted"
