---
version: 1
name: Download Video and Share to TikTok
app: Chrome
ios_min: "17.0"
locale: "en_US"
tags: ["chrome", "download", "video", "tiktok", "share", "upload"]
params:
  - name: VIDEO_URL
    description: "Direct download URL of the video to upload"
    required: true
  - name: VIDEO_TITLE
    description: "Caption/description to type into TikTok's post editor"
    required: false
---

Download a video from a URL in Chrome and share it directly to TikTok for posting.

## Rules

- **Coordinates**: **MUST** use `describe_screen` to get tap coordinates — never estimate from screenshot pixels.
- **Failure recovery**: If any step fails or the UI is not in the expected state, **do NOT try alternative approaches, workarounds, or ad-hoc recovery**. Immediately kill **both Chrome and TikTok** (force-quit via App Switcher) and restart the entire skill from **Step 1**.

- **Fixed coordinates** (OCR returns wrong / merged values for these — use the literal coords):
  - **Next** button: **(248, 680)** (OCR returns wrong Y)
  - **Favorites** tab in sound picker: **(145, 411)** (OCR merges "Favorites Recent" into a single element at ~(175, 411) when For You is the active tab; tap (145, 411) to switch, after which OCR will read each tab separately)
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
7. Copy the URL to macOS clipboard: run `printf '%s' "${VIDEO_URL}" | pbcopy` (use `printf` not `echo -n`; safe even if the URL contains `$`, `` ` ``, `"`).
8. Paste with **Cmd+V**
9. Press **Return**

### Part 2: Share video to TikTok

10. Tap "DOWNLOAD". Wait for the "Download complete" banner to appear at the bottom of the screen
11. Tap "OPEN IN..." on the download complete banner to open the share sheet
12. Wait for the share sheet to appear
13. Use `describe_screen` to check if "TikTok" is in the app icon row. If not visible, swipe right (from_x=200, to_x=50, duration 1000ms) on the app row to reveal more apps, then `describe_screen` again. Repeat until "TikTok" appears, then tap it.
14. Wait for TikTok to open. A "Share on TikTok" modal appears with **Video** and **Message** buttons. Use `describe_screen` to locate the "Video" button, then tap it to enter the video editing flow.
15. If "iPhone camera is not available from Mac" dialog appears, dismiss it by running `dismiss_camera_dialog.sh` or using cliclick to click OK at the dialog's screen position

### Part 3: Touch the sound picker (clear default music if any) → Next

Don't pick a song yet — that happens in Part 6. But TikTok sometimes auto-attaches a default song; we need to remove it here so the post editor doesn't carry the wrong music. Even when there's no default, the open-then-close is needed so the editor is in a clean state for Next.

16. Use `describe_screen` to locate **`/ Add sound`** (or **`Add sound`**) at the top center (~`(167, 113)`). Tap it. The sound picker opens (Commercial Sounds sheet on top).
17. Dismiss the picker by tapping the upper video-preview area (~`(167, 200)`). The video editor reappears.
18. `describe_screen` and look for a `♪ <song name> ×` chip at the top of the editor — that means TikTok auto-attached a default song. If the chip is present, tap the **`×`** on it to detach. If no such chip exists, do nothing and continue to Step 19.
19. Tap **Next** directly at fixed coordinates **(248, 680)**. The OCR returns incorrect Y for this button.
20. Wait for the post editing screen (caption, hashtags).

### Part 4: Add description and attach a product link

21. Tap the "Add description..." text field. If `VIDEO_TITLE` is non-empty, copy it to clipboard with `printf '%s' "${VIDEO_TITLE}" | pbcopy` then paste with **Cmd+V**. If empty, leave the description blank and proceed.
22. Tap **Add link** on the post editor.
23. In the picker, tap **Product**. The "Add product links / Your showcase" page opens.
24. Tap **Add** on the first product in Your showcase.
25. If an **"Earn extra commission"** modal appears (asks to pick countries for cross-border distribution), tap the red **Continue** button at the bottom of the modal (roughly `(166, 607)` on a 334x735 mirroring window — confirm via `describe_screen`).
26. The **"Rename product"** confirmation page appears (shows the chosen product, a pre-filled product name field, and a red **Add** button at the bottom). Tap the bottom **Add** button to finalize.
27. Verify: back on the post editor, the row under **Add link** now shows a chip with the product title and a `×` button. Screenshot as `tiktok_product_added`.

### Part 5: Back to the video editor

28. Use `describe_screen` to locate the **`<`** back button at the top-left of the post editor (expected near `(25, 92)` on a 334x735 mirroring window — always confirm via OCR). Tap it. The post editor's draft (description + product chip) is preserved automatically; you'll come back to it after Part 6.

### Part 6: Pick music, mute original, return to post editor

The flow has a quirk: tapping "Add sound" first lands on the **Commercial Sounds** picker (TikTok-Shop variant). The standard sound picker (with Hot / For You / Favorites / Recent tabs) is _underneath_, and only becomes visible after you close the Commercial Sounds overlay.

29. Use `describe_screen` to locate **`/ Add sound`** (or **`Add sound`**) at the top center of the editor (typically near `(167, 113)` on a 334x735 mirroring window). Tap it. The **Commercial Sounds** sheet slides up.
30. `describe_screen` to identify which picker is on screen:
    - If `"Commercial Sounds"` title is present → tap its top-left **`X`** to peel off the Commercial layer; the standard picker (Hot / For You / Favorites / Recent tabs) appears underneath.
    - If `Hot` / `For You` / `Favorites` / `Recent` tabs are already visible (standard picker opened directly, no Commercial overlay) → skip the X tap and continue.
31. Tap the **Favorites** tab at fixed coordinates **(145, 411)** — do NOT trust `describe_screen` for this tap. When For You is the active tab, OCR merges "Favorites Recent" into a single element at ~(175, 411), which is between the two labels and lands wrong. After the tap, `describe_screen` again to confirm Favorites is now active (it will then return all 4 tabs separately at distinct coords).
32. From the favorited songs list, tap the **first row** (the topmost song title — its Y is typically around 448 immediately under the tab bar). After the tap, the selected row should show a red border and `✂` (trim) + 🔖 (saved) icons appear on its right.
33. **Make sure the original audio is muted** — but DON'T blindly tap. Selecting a Favorite song often auto-mutes the original; tapping again would un-mute. Procedure:
    a. `describe_screen` and inspect the **Original** icon at the bottom-left toolbar (~`(62, 691)`).
    b. Take a `screenshot` and look at the mic icon visually: a mic with a **diagonal slash** = already muted; a plain mic = original audio still on.
    c. If already muted → do nothing, continue to Step 34.
    d. If unmuted → tap the Original button (~`(62, 691)`) and re-screenshot to confirm the slash now appears.
34. Dismiss the sound picker by tapping the upper video-preview area (around `(167, 200)` — anywhere above the tab bar Y works). The video editor returns; the chosen music name now appears as a `♪ <song name> ×` chip at the top of the editor — confirm via `describe_screen`.
35. Tap **Next** directly at fixed coordinates **(248, 680)**. The OCR returns incorrect Y for this button.
36. Wait for the post editing screen. Verify via `describe_screen` that the previously-entered description AND product chip are still present (TikTok preserves the draft). If either is missing, stop and report — do NOT post a half-broken video.

### Part 7: Publish

37. Use `describe_screen` to locate the red **Post** button at the bottom-right of the post editor (label `"Post"` or `"+ Post"`; on a 334x735 mirroring window it sits near `(246, 679)` — but ALWAYS confirm via OCR before tapping, this is the destructive publish action).
38. Tap Post.
39. Wait until the post editor is **gone** — the screen transitions to the TikTok feed / profile (or shows a "Posted" / "Uploading..." indicator briefly). Verify via `describe_screen`: the `"Add description..."` field and the `"Drafts"` / `"Post"` buttons must NOT be visible anymore.
40. If a "Save to drafts?" / "Discard?" prompt appears instead of a successful publish, the post failed — stop and report the prompt text verbatim. Do NOT auto-discard or auto-save.

