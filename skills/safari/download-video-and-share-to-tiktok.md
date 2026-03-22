---
version: 1
name: Download Video and Share to TikTok
app: Safari
ios_min: "17.0"
locale: "en_US"
tags: ["safari", "download", "video", "tiktok", "share", "upload"]
---

Download a video from a URL in Safari and share it directly to TikTok for posting.

## Steps

1. Launch **Safari**
2. Wait for Safari to appear
3. Open a new tab with **Cmd+T**
4. Tap the address bar (search field at the bottom)
5. Type "${VIDEO_URL}"
6. Press **Return**
7. Wait for the download dialog to appear ("Do you want to download...")
8. Tap "Download"
9. Wait for the download to complete (the download icon in the address bar will show a blue checkmark)
10. Tap the page settings icon to the left of the address bar (the icon next to the URL)
11. Wait for the menu to appear
12. Tap "Downloads"
13. Wait for the Downloads panel to appear
14. Tap the first downloaded file (most recent download) to open it in Quick Look
15. Wait 15 seconds for the video to finish playing, then tap the center of the black bar at the bottom of the screen to reveal the playback controls overlay
16. Tap the share button (box with arrow icon) in the bottom-right of the Quick Look toolbar
17. Wait for the share sheet to appear
18. Tap "TikTok" in the share sheet app row
19. Wait for TikTok's share/post screen to appear
20. If "iPhone camera is not available from Mac" dialog appears, dismiss it by running `dismiss_camera_dialog.sh` or using cliclick to click OK at the dialog's screen position
21. Tap "Add sound" at the top center of the editing screen
21. Wait for the sound picker to appear
22. Tap "Original" to mute the original video audio
23. Tap "For you" tab to browse recommended music
24. Swipe up to scroll down the music list
25. Tap a random music track to select it
26. Tap the upper-center area of the screen to return to the video editor
27. Tap "Next" to proceed past any editing/trimming screen
28. Wait for the post editing screen (caption, hashtags)
29. If a caption text field is visible:
    1. Tap the caption/description text field
    2. Type "${VIDEO_TITLE:-}"
30. Tap "Post"
31. Wait for upload to complete
32. Screenshot: "tiktok_posted"
