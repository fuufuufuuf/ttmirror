---
version: 1
name: Upload Video to TikTok
app: TikTok
ios_min: "17.0"
locale: "en_US"
tags: ["tiktok", "upload", "video", "social"]
---

Upload the most recent video from Photos to TikTok with an optional caption.

## Steps

1. Launch **TikTok**
2. Wait for the TikTok home feed to appear
3. Tap the "+" button at the bottom center of the screen (create/post button)
4. Wait for the camera screen to appear
5. Tap "Upload" (bottom-right of the camera screen)
6. Wait for the photo library picker to appear
7. If "Allow TikTok to access your photos" dialog appears:
   1. Tap "Allow Full Access"
8. Tap the most recent video (first item in the grid)
9. Wait for video preview or trimming screen
10. Tap "Next" to proceed past trimming/editing
11. Wait for the post editing screen (caption, hashtags)
12. If a caption text field is visible:
    1. Tap the caption/description text field
    2. Type "${CAPTION:-}"
13. Tap "Post"
14. Wait for upload to complete
15. Screenshot: "tiktok_posted"
