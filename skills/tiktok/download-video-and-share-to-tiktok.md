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
- **Image bandwidth**: every `screenshot` and every `describe_screen` (without `omit_screenshot: true`) sends a ~400KB image to the model and adds ~500ms-1s per call. Pass `omit_screenshot: true` whenever you only need OCR text / coordinates (the typical "find element to tap" case). Reserve full images for steps that explicitly call out **visual analysis** below (icon shape, mic slash, button color). Never call `screenshot` immediately after `describe_screen` — describe_screen's default response already includes the same frame.
- **Completion markers (REQUIRED — caller uses these to detect success vs silent abort)**:
  - On **successful publish** (final Step verified post editor is gone), emit this exact final line: `UPLOAD_VIDEO_POSTED: ${VIDEO_URL}`.
  - On **any abort** (Part 0 mirroring still paused after wake retry, mirroring pauses mid-skill, error toast on Post, "Save to drafts?" prompt, or any other reason you stop before posting), emit this exact final line: `UPLOAD_VIDEO_ABORTED: <one-line reason>`. Examples: `UPLOAD_VIDEO_ABORTED: iPhone Mirroring paused, manual unlock required`, `UPLOAD_VIDEO_ABORTED: Save-to-drafts prompt appeared after Post`. Do NOT continue subsequent steps after emitting ABORTED.
  - Polite narrations like "please unlock the iPhone and let me know when ready" without the marker are FORBIDDEN — the caller cannot detect them and would silently mark the record as posted in Feishu.
- **Mirroring paused mid-skill**: if any mirroir tool returns "Mirroring paused" / "Target 'iphone' is paused" mid-skill, call `screenshot` once to wake, then retry the failed call ONCE. If still paused, emit `UPLOAD_VIDEO_ABORTED: iPhone Mirroring paused mid-skill` and stop.
- **Failure recovery**: If any step fails or the UI is not in the expected state, **do NOT try alternative approaches, workarounds, or ad-hoc recovery**. Immediately kill **both Chrome and TikTok** (force-quit via App Switcher) and restart the entire skill from **Step 1**.

- **Fixed coordinates** (OCR returns wrong / merged values for these — use the literal coords):
  - **Next** button: **(248, 680)** (OCR returns wrong Y)
  - **Favorites** tab in sound picker: **(145, 411)** (OCR merges "Favorites Recent" into a single element at ~(175, 411) when For You is the active tab; tap (145, 411) to switch, after which OCR will read each tab separately)
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
7. Type the URL directly with `type_text` `${VIDEO_URL}`. Do **not** use `pbcopy` + Cmd+V — Universal Clipboard does not sync from script-driven `pbcopy` to iOS via iPhone Mirroring, so Cmd+V will paste a stale value.
8. **Do NOT press Return.** iOS Chrome's omnibox can hijack Return via inline autocomplete: if browsing history contains a same-prefix URL with different case-folding (e.g. `dYtNvSsZb` vs. `dytnvsszb`), Return navigates to the history version, not what you typed. Cloudinary paths are case-sensitive — a hijack 404s the download and breaks the rest of the skill. Tap the "what-you-typed" globe-icon dropdown row instead:
    a. `describe_screen` (with default `omit_screenshot: false` — visual analysis required) to inspect the omnibox dropdown rows below the address bar. Each row has an `icon` element near `x≈35` followed by one or more URL text lines. The describe_screen response includes both OCR text AND the image — use both. Do NOT call `screenshot` separately; it would be a redundant second image.
    b. Filter to rows whose URL text starts with the **literal lowercase `${VIDEO_URL}` prefix**. Reject any row showing differently-cased characters (those are polluted history entries — they are exactly what we are trying to avoid).
    c. Among the lowercase-matching rows, visually identify the row whose left-side icon is a 🌐 **globe** (a circular outline with grid lines, meaning "navigate to URL"). Reject rows with a 🔍 **magnifying glass** (those run a Google search of the URL string instead of navigating) and rows with a colored **favicon / brand logo** (those are history entries with the URL's saved casing).
    d. `tap` the URL text portion of the globe-icon row (not the icon itself).
    e. Wait for the page to load, then `describe_screen` `omit_screenshot: true` to verify: the address bar host is the expected domain (e.g. `res.cloudinary.com`) and expected content is visible (e.g. a `DOWNLOAD` button + `<filename>.mp4 (<size>)`). If the page is a Google search results page or a different URL host, the wrong row was tapped.
    f. If no row satisfies both "lowercase-prefix match" AND "globe icon" — **stop the skill** and emit this exact final line: `URL_AUTOCOMPLETE_HIJACK_GUARD: ${VIDEO_URL}`

### Part 2: Share video to TikTok

10. Tap "DOWNLOAD". Wait for the "Download complete" banner to appear at the bottom of the screen
11. Tap "OPEN IN..." on the download complete banner to open the share sheet
12. Wait for the share sheet to appear
13. Use `describe_screen` `omit_screenshot: true` to check if "TikTok" is in the app icon row. If not visible, swipe right (from_x=200, to_x=50, duration 1000ms) on the app row to reveal more apps, then `describe_screen` `omit_screenshot: true` again. Repeat until "TikTok" appears, then tap it.
14. Wait for TikTok to open. A "Share on TikTok" modal appears with **Video** and **Message** buttons. Use `describe_screen` `omit_screenshot: true` to locate the "Video" button, then tap it to enter the video editing flow.

### Part 3: Touch the sound picker (clear default music if any) → Next

Don't pick a song yet — that happens in Part 6. But TikTok sometimes auto-attaches a default song; we need to remove it here so the post editor doesn't carry the wrong music. Even when there's no default, the open-then-close is needed so the editor is in a clean state for Next.

15. Use `describe_screen` `omit_screenshot: true` to locate **`/ Add sound`** (or **`Add sound`**) at the top center (~`(167, 113)`). Tap it. The sound picker opens (Commercial Sounds sheet on top).
16. Dismiss the picker by tapping the upper video-preview area (~`(167, 200)`). The video editor reappears.
17. `describe_screen` `omit_screenshot: true` and look for a `♪ <song name> ×` chip at the top of the editor — that means TikTok auto-attached a default song. If the chip is present, tap the **`×`** on it to detach. If no such chip exists, do nothing and continue to Step 18.
18. Tap **Next** directly at fixed coordinates **(248, 680)**. The OCR returns incorrect Y for this button.
19. Wait for the post editing screen (caption, hashtags).

### Part 4: Add description and attach a product link

20. Tap the "Add description..." text field. If `VIDEO_TITLE` is non-empty, type it directly with `type_text` `${VIDEO_TITLE}`. If empty, leave the description blank and proceed. Do **not** use `pbcopy` + Cmd+V (Universal Clipboard does not sync reliably under iPhone Mirroring).
21. Tap **Add link** on the post editor.
22. In the picker, tap **Product**. The "Add product links / Your showcase" page opens.
23. Tap **Add** on the first product in Your showcase.
24. If an **"Earn extra commission"** modal appears (asks to pick countries for cross-border distribution), tap the red **Continue** button at the bottom of the modal (roughly `(166, 607)` on a 334x735 mirroring window — confirm via `describe_screen` `omit_screenshot: true`).
25. The **"Rename product"** confirmation page appears (shows the chosen product, a pre-filled product name field, and a red **Add** button at the bottom). Tap the bottom **Add** button to finalize.
26. Verify: back on the post editor, the row under **Add link** now shows a chip with the product title and a `×` button. Use `describe_screen` `omit_screenshot: true` to confirm the product chip text is present (no archival screenshot needed).

### Part 5: Back to the video editor

27. Use `describe_screen` `omit_screenshot: true` to locate the **`<`** back button at the top-left of the post editor (expected near `(25, 92)` on a 334x735 mirroring window — always confirm via OCR). Tap it. The post editor's draft (description + product chip) is preserved automatically; you'll come back to it after Part 6.

### Part 6: Pick music, mute original, return to post editor

The flow has a quirk: tapping "Add sound" first lands on the **Commercial Sounds** picker (TikTok-Shop variant). The standard sound picker (with Hot / For You / Favorites / Recent tabs) is _underneath_, and only becomes visible after you close the Commercial Sounds overlay.

28. Use `describe_screen` `omit_screenshot: true` to locate **`/ Add sound`** (or **`Add sound`**) at the top center of the editor (typically near `(167, 113)` on a 334x735 mirroring window). Tap it. The **Commercial Sounds** sheet slides up.
29. `describe_screen` `omit_screenshot: true` to identify which picker is on screen:
    - If `"Commercial Sounds"` title is present → tap its top-left **`X`** to peel off the Commercial layer; the standard picker (Hot / For You / Favorites / Recent tabs) appears underneath.
    - If `Hot` / `For You` / `Favorites` / `Recent` tabs are already visible (standard picker opened directly, no Commercial overlay) → skip the X tap and continue.
30. Tap the **Favorites** tab at fixed coordinates **(145, 411)** — do NOT trust `describe_screen` for this tap. When For You is the active tab, OCR merges "Favorites Recent" into a single element at ~(175, 411), which is between the two labels and lands wrong. After the tap, `describe_screen` `omit_screenshot: true` again to confirm Favorites is now active (it will then return all 4 tabs separately at distinct coords).
31. From the favorited songs list, tap the **first row** (the topmost song title — its Y is typically around 448 immediately under the tab bar). After the tap, the selected row should show a red border and `✂` (trim) + 🔖 (saved) icons appear on its right.
32. **Make sure the original audio is muted** — Tap the Original button (~`(62, 691)`) and call `screenshot` once to confirm the slash now appears on Mic icon.
33. Dismiss the sound picker by tapping the upper video-preview area (around `(167, 200)` — anywhere above the tab bar Y works). The video editor returns; the chosen music name now appears as a `♪ <song name> ×` chip at the top of the editor — confirm via `describe_screen` `omit_screenshot: true`.
34. Tap **Next** directly at fixed coordinates **(248, 680)**. The OCR returns incorrect Y for this button.
35. Wait for the post editing screen. Verify via `describe_screen` `omit_screenshot: true` that the previously-entered description AND product chip are still present (TikTok preserves the draft). If either is missing, stop and report — do NOT post a half-broken video.

### Part 7: Publish

36. Use `describe_screen` `omit_screenshot: true` to locate the red **Post** button at the bottom-right of the post editor (label `"Post"` or `"+ Post"`; on a 334x735 mirroring window it sits near `(246, 679)` — but ALWAYS confirm via OCR before tapping, this is the destructive publish action).
37. Tap Post.
38. Wait until the post editor is **gone** — the screen transitions to the TikTok feed / profile (or shows a "Posted" / "Uploading..." indicator briefly). Verify via `describe_screen` `omit_screenshot: true`: the `"Add description..."` field and the `"Drafts"` / `"Post"` buttons must NOT be visible anymore.
39. If a "Save to drafts?" / "Discard?" prompt appears instead of a successful publish, the post failed — emit `UPLOAD_VIDEO_ABORTED: Save-to-drafts/Discard prompt appeared after Post` and stop. Do NOT auto-discard or auto-save.
40. **Emit the success marker** as the final line: `UPLOAD_VIDEO_POSTED: ${VIDEO_URL}`. This is the only signal the caller uses to mark the Feishu record as posted. Without this marker, the caller treats the run as a silent abort and writes a failure note instead.

