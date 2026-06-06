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

- **Always tap at the EXACT (x, y) returned by the most recent `describe_screen`**: Never use approximate, remembered, or previously-cached coordinates. Each screen capture returns fresh coordinates — always read the current result and tap at those exact values. This applies to every tap: tab bar icons, buttons, list items, etc.
- **Image bandwidth**: every `screenshot` and every `describe_screen` (without `omit_screenshot: true`) sends a ~400KB image to the model and adds ~500ms-1s per call. Pass `omit_screenshot: true` whenever you only need OCR text / coordinates (the typical "find element to tap" case). Reserve full images for steps that explicitly call out **visual analysis** below (icon shape, mic slash, button color). Never call `screenshot` immediately after `describe_screen` — describe_screen's default response already includes the same frame.
- **Completion markers (REQUIRED — caller uses these to detect success vs silent abort)**:
  - On **successful publish** (final Step verified post editor is gone), emit this exact final line: `UPLOAD_VIDEO_POSTED: ${VIDEO_URL}`.
  - On **any abort** (Part 0 mirroring still paused after wake retry, mirroring pauses mid-skill, error toast on Post, "Save to drafts?" prompt, or any other reason you stop before posting), emit this exact final line: `UPLOAD_VIDEO_ABORTED: <one-line reason>`. Examples: `UPLOAD_VIDEO_ABORTED: iPhone Mirroring paused, manual unlock required`, `UPLOAD_VIDEO_ABORTED: Save-to-drafts prompt appeared after Post`. Do NOT continue subsequent steps after emitting ABORTED.
  - Polite narrations like "please unlock the iPhone and let me know when ready" without the marker are FORBIDDEN — the caller cannot detect them and would silently mark the record as posted in Feishu.
- **Mirroring paused mid-skill**: if any mirroir tool returns "Mirroring paused" / "Target 'iphone' is paused" mid-skill, call `screenshot` once to wake, then retry the failed call ONCE. If still paused, emit `UPLOAD_VIDEO_ABORTED: iPhone Mirroring paused mid-skill` and stop.
- **Failure recovery**: If any step fails or the UI is not in the expected state, **do NOT try alternative approaches, workarounds, or ad-hoc recovery**. Immediately kill **both Chrome and TikTok** (force-quit via App Switcher) and restart the entire skill from **Step 1**.

- **Keyboard shortcuts** (iPhone Mirroring):
  - **Cmd+1**: Home Screen
  - **Cmd+2**: App Switcher
  - **Cmd+3**: Spotlight Search

## Steps
### Part 0: Ensure iPhone Mirroring is active

1. Call `status` to check if mirroring is active
2. If the status is **not** active (e.g. paused or no window), call `screenshot` to wake up the mirroring session, then call `status` again to confirm it is now active
3. If still not active after retry, emit `UPLOAD_VIDEO_ABORTED: iPhone Mirroring paused, manual unlock required` and stop. Do NOT proceed to Part 1.

### Part 1: Open Chrome and navigate to video URL

1. Press **Cmd+1** to go to the Home Screen
2. Press **Cmd+3** to open Spotlight Search. The search field is auto-focused — **do NOT tap it** (the tap is unreliable and unnecessary).
3. `type_text` `chrome` directly, then press **Return** to launch chrome.
4. Wait for chrome to appear
5. Open a new tab with **Cmd+T**
6. Press **Cmd+L** to focus the address bar, then press **Cmd+A** + **Delete** to clear any stale text in the address bar (no-op if already empty).
7. Type the URL directly with `type_text` `${VIDEO_URL}`, then press **Return** to navigate. Do **not** use `pbcopy` + Cmd+V — Universal Clipboard does not sync from script-driven `pbcopy` to iOS via iPhone Mirroring, so Cmd+V will paste a stale value. Wait for the page to load, then `describe_screen` `omit_screenshot: true` to verify: the address bar host is the expected domain (e.g. `res.cloudinary.com`) and expected content is visible (e.g. a `DOWNLOAD` button + `<filename>.mp4 (<size>)`).

### Part 2: Share video to TikTok

8. Tap "DOWNLOAD" (cloudinary's page renders the filename `<name>.mp4 (<size>)` and the blue DOWNLOAD button as one composite element; use `describe_screen` to get the "DOWNLOAD" label coordinates and tap there directly)
9. Use `describe_screen` `omit_screenshot: true` to locate **"OPEN IN..."** on the download complete banner. **Tap at the EXACT coordinates returned by describe_screen — do NOT estimate or adjust the coordinates (e.g. do not tap "the left part" at a different X).** Open the share sheet, then wait for it to appear.
11. Use `describe_screen` `omit_screenshot: true` to check if "TikTok" is visible. **To determine the correct swipe Y coordinate, always look at elements with text labels (e.g., "Journal", "Mail", "AirDrop") — their Y coordinate marks the actual vertical position of the app icons row. Do NOT estimate based on anonymous "icon" elements, as they appear at many different Y values and will mislead you.** If TikTok is not visible, swipe the app icons row from right to left with enough amplitude (at least 200px) to reach the end where TikTok lives. After each swipe, call `describe_screen` `omit_screenshot: true` to verify. Repeat until "TikTok" appears, then tap it.
12. Wait for TikTok to open. A "Share on TikTok" modal appears with **Video** and **Message** buttons. Use `describe_screen` `omit_screenshot: true` to locate the "Video" button, then tap it to enter the video editing flow.

### Part 3: Touch the sound picker (clear default music if any) → Next

Don't pick a song yet — that happens in Part 6. But TikTok sometimes auto-attaches a default song; we need to remove it here so the post editor doesn't carry the wrong music. Even when there's no default, the open-then-close is needed so the editor is in a clean state for Next.

13. Use `describe_screen` `omit_screenshot: true` to locate **`/ Add sound`** (or **`Add sound`**) at the top center. Tap it. The sound picker opens. **Wait 5 seconds** for the picker animation to fully settle before proceeding to Step 14.
14. **Mute Sound**: Use `describe_screen` `omit_screenshot: false` to locate the **Sound icon** (music note icon — second from the bottom in the icon bar, labeled "Sound"). Take a `screenshot` to check if the Sound icon already shows a slash (muted). If already slashed, skip this step. If not slashed, tap the Sound icon to slash it, then `screenshot` again to confirm the slash.
15. **Mute Original**: Use `describe_screen` `omit_screenshot: false` to locate the **Original button** (first from the bottom in the icon bar, labeled "Original"). Take a `screenshot` to check if the Original button already shows a slash (muted). If already slashed, skip this step. If not slashed, tap the Original button to slash it, then `screenshot` again to confirm the slash.
16. **Verify both are muted**: Take a `screenshot` and confirm both the Sound icon and the Original button show slashes. If either is still not slashed, go back to **Step 14** and repeat the mute process for the un-slashed icon(s). Continue until both icons show slashes before proceeding.
17. Dismiss the picker by tapping the upper video-preview area (~`(167, 200)`). The video editor reappears.
18. Tap **Next**. Wait for the post editing screen (caption, hashtags).

### Part 4: Add description and attach a product link

19. Tap the "Add description..." text field. If `VIDEO_TITLE` is non-empty, type it directly with `type_text` `${VIDEO_TITLE}`. If empty, leave the description blank and proceed. Do **not** use `pbcopy` + Cmd+V (Universal Clipboard does not sync reliably under iPhone Mirroring).
20. Tap **Add link** on the post editor.
21. In the picker, tap **Product**. The "Add product links / Your showcase" page opens.
22. Tap **Add** on the first product in Your showcase.
23. If an **"Earn extra commission"** modal appears (asks to pick countries for cross-border distribution), tap the red **Continue** button at the bottom of the modal (roughly `(166, 607)` on a 334x735 mirroring window — confirm via `describe_screen` `omit_screenshot: true`).
24. The **"Rename product"** confirmation page appears (shows the chosen product, a pre-filled product name field, and a red **Add** button at the bottom). Tap the bottom **Add** button to finalize.
25. Verify: back on the post editor, the row under **Add link** now shows a chip with the product title and a `×` button. Use `describe_screen` `omit_screenshot: true` to confirm the product chip text is present (no archival screenshot needed).

### Part 5: Back to the video editor

26. Use `describe_screen` `omit_screenshot: true` to locate the **`<`** back button at the top-left of the post editor (expected near `(25, 92)` on a 334x735 mirroring window — always confirm via OCR). Tap it. The post editor's draft (description + product chip) is preserved automatically; you'll come back to it after Part 6.

### Part 6: Pick music, mute original, return to post editor

The flow has a quirk: tapping "Add sound" first lands on the **Commercial Sounds** picker (TikTok-Shop variant). The standard sound picker (with Hot / For You / Favorites / Recent tabs) is _underneath_, and only becomes visible after you close the Commercial Sounds overlay.

27. Use `describe_screen` `omit_screenshot: true` to locate **`/ Add sound`** (or **`Add sound`**) at the top center of the editor (typically near `(167, 113)` on a 334x735 mirroring window). Tap it. The **Commercial Sounds** sheet slides up.
28. Use `describe_screen` `omit_screenshot: true` to identify which picker is on screen:
    - If `"Commercial Sounds"` title is present → tap its **top-left `X`** (the small X icon at ~`(30, 89)` — left of the "Commercial Sounds" title, not the filter icon on the right) to close the Commercial Sounds layer. After tapping X, the standard picker (Hot / For You / Favorites / Recent tabs) should appear underneath. **Do NOT tap the back button** — that would reopen Commercial Sounds.
    - If `Hot` / `For You` / `Favorites` / `Recent` tabs are already visible (standard picker opened directly, no Commercial overlay) → skip the X tap and continue.
29. After closing Commercial Sounds, verify that the standard picker tabs (Hot / For You / Favorites / Recent) are now visible. If Commercial Sounds is still present, tap its **`X`** again. If tabs appear but "Commercial Sounds" is also still showing, try tapping outside the Commercial Sounds sheet (e.g. on the video preview area at ~`(167, 200)`) to fully dismiss it.
30. Use `describe_screen` `omit_screenshot: true` to locate the **Favorites** tab. **Always confirm the tab bar's actual Y coordinate from the OCR output. Do NOT use a guessed or remembered Y value; read it fresh from each `describe_screen` result.** Tap Favorites at the coordinates returned by OCR. After the tap, `describe_screen` `omit_screenshot: true` again to confirm Favorites is now active.
31. From the favorited songs list, tap the **first row** (the topmost song title — its Y is typically around 448 immediately under the tab bar). After the tap, the selected row should show a red border and `✂` (trim) + 🔖 (saved) icons appear on its right.
32. Dismiss the sound picker by tapping the upper video-preview area (around `(167, 200)` — anywhere above the tab bar Y works). The video editor returns; the chosen music name now appears as a `♪ <song name> ×` chip at the top of the editor — confirm via `describe_screen` `omit_screenshot: true`.
33. Tap **Next**. Verify via `describe_screen` `omit_screenshot: true` that the previously-entered description AND product chip are still present (TikTok preserves the draft). If either is missing, stop and report — do NOT post a half-broken video.

### Part 7: Publish

34. Use `describe_screen` `omit_screenshot: true` to locate the red **Post** button at the bottom-right of the post editor (label `"Post"` or `"+ Post"`; on a 334x735 mirroring window it sits near `(246, 679)` — but ALWAYS confirm via OCR before tapping, this is the destructive publish action).
35. Tap Post.
36. Wait until the post editor is **gone** — the screen transitions to the TikTok feed / profile (or shows a "Posted" / "Uploading..." indicator briefly). Verify via `describe_screen` `omit_screenshot: true`: the `"Add description..."` field and the `"Drafts"` / `"Post"` buttons must NOT be visible anymore.
37. If a "Save to drafts?" / "Discard?" prompt appears instead of a successful publish, the post failed — emit `UPLOAD_VIDEO_ABORTED: Save-to-drafts/Discard prompt appeared after Post` and stop. Do NOT auto-discard or auto-save.
38. **Emit the success marker** as the final line: `UPLOAD_VIDEO_POSTED: ${VIDEO_URL}`. This is the only signal the caller uses to mark the Feishu record as posted. Without this marker, the caller treats the run as a silent abort and writes a failure note instead.

