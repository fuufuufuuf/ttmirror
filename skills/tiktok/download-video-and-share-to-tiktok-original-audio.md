---
version: 1
name: Download Video and Share to TikTok (Original Audio, No Product)
app: Chrome
ios_min: "17.0"
locale: "en_US"
tags: ["chrome", "download", "video", "tiktok", "share", "upload", "original-audio", "fallback"]
params:
  - name: VIDEO_URL
    description: "Direct download URL of the video to upload"
    required: true
  - name: VIDEO_TITLE
    description: "Caption/description to type into TikTok's post editor"
    required: false
---

Fallback variant of the standard upload skill, used when product addition to the showcase failed (caller routes here from `auto_upload.py`). Differences from the full skill:

- **Uses the video's ORIGINAL audio** — no Favorites tab, no song selection, no muting of the original audio.
- **No product link** — the post editor's `Add link → Product` flow is skipped entirely.

The aim is to still get the video posted (just degraded) instead of dropping it.

## Rules

- **Coordinates**: **MUST** use `describe_screen` to get tap coordinates — never estimate from screenshot pixels.
- **Image bandwidth**: every `screenshot` and every `describe_screen` (without `omit_screenshot: true`) sends a ~400KB image to the model and adds ~500ms-1s per call. Pass `omit_screenshot: true` whenever you only need OCR text / coordinates (the typical "find element to tap" case). Reserve full images for steps that explicitly call out **visual analysis** below (icon shape, etc.). Never call `screenshot` immediately after `describe_screen` — describe_screen's default response already includes the same frame.
- **Completion markers (REQUIRED — caller uses these to detect success vs silent abort)**:
  - On **successful publish** (final Step verified post editor is gone), emit this exact final line: `UPLOAD_VIDEO_POSTED: ${VIDEO_URL}`.
  - On **any abort** (Part 0 mirroring still paused after wake retry, mirroring pauses mid-skill, error toast on Post, "Save to drafts?" prompt, or any other reason you stop before posting), emit this exact final line: `UPLOAD_VIDEO_ABORTED: <one-line reason>`. Do NOT continue subsequent steps after emitting ABORTED.
  - Polite narrations like "please unlock the iPhone and let me know when ready" without the marker are FORBIDDEN — the caller cannot detect them and would silently mark the record as posted in Feishu.
- **Mirroring paused mid-skill**: if any mirroir tool returns "Mirroring paused" / "Target 'iphone' is paused" mid-skill, call `screenshot` once to wake, then retry the failed call ONCE. If still paused, emit `UPLOAD_VIDEO_ABORTED: iPhone Mirroring paused mid-skill` and stop.
- **Failure recovery**: If any step fails or the UI is not in the expected state, **do NOT try alternative approaches, workarounds, or ad-hoc recovery**. Immediately kill **both Chrome and TikTok** (force-quit via App Switcher) and restart the entire skill from **Step 1**.

- **Fixed coordinates** (OCR returns wrong / merged values for these — use the literal coords):
  - **Next** button: **(248, 680)** (OCR returns wrong Y)
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
13. Use `describe_screen` `omit_screenshot: true` to check if "TikTok" is in the app icon row. If not visible, swipe the row with `mcp__mirroir__swipe(from_x=50, from_y=460, to_x=300, to_y=460, duration_ms=1000)` — a single swipe of this magnitude typically jumps to the end of the row where TikTok lives. **Never** call it in the reverse direction (e.g. `from_x=200, to_x=50`): empirically, short leftward swipes are silently dropped by mirroir; only low-to-high X reliably advances the row. After each swipe, `describe_screen` `omit_screenshot: true` to verify. Repeat the same call (not the reverse) until "TikTok" appears, then tap it.
14. Wait for TikTok to open. A "Share on TikTok" modal appears with **Video** and **Message** buttons. Use `describe_screen` `omit_screenshot: true` to locate the "Video" button, then tap it to enter the video editing flow.

### Part 3: Go directly to Next

The fallback path does NOT touch any audio UI at all. Whatever audio state the editor lands in (original audio, or a default-attached song if TikTok auto-attached one) is accepted as-is. Do NOT do anything besides tapping Next:

- Do NOT tap `Add sound` / `/ Add sound` at the top center (~`(167, 113)`). Do not open the sound picker at all.
- Do NOT tap any `♪ <song> ×` chip at the top of the editor. Leave any auto-attached default song chip alone.
- Do NOT tap the Original mic icon at the bottom-left toolbar (~`(62, 691)`).
- Do NOT open Favorites / Hot / For You / Recent.

15. Tap **Next** directly at fixed coordinates **(248, 680)**. The OCR returns incorrect Y for this button.
16. Wait for the post editing screen (caption, hashtags).

### Part 4: Add description (no product) and Post

17. Tap the "Add description..." text field. If `VIDEO_TITLE` is non-empty, type it directly with `type_text` `${VIDEO_TITLE}`. If empty, leave the description blank and proceed. Do **not** use `pbcopy` + Cmd+V (Universal Clipboard does not sync reliably under iPhone Mirroring).
18. **Skip** the "Add link → Product → showcase → Add" flow. This skill must NOT add any product link to the post.
19. Use `describe_screen` `omit_screenshot: true` to locate the red **Post** button at the bottom-right of the post editor (label `"Post"` or `"+ Post"`; on a 334x735 mirroring window it sits near `(246, 679)` — but ALWAYS confirm via OCR before tapping, this is the destructive publish action).
20. Tap Post.
21. Wait until the post editor is **gone** — the screen transitions to the TikTok feed / profile (or shows a "Posted" / "Uploading..." indicator briefly). Verify via `describe_screen` `omit_screenshot: true`: the `"Add description..."` field and the `"Drafts"` / `"Post"` buttons must NOT be visible anymore.
22. If a "Save to drafts?" / "Discard?" prompt appears instead of a successful publish, the post failed — emit `UPLOAD_VIDEO_ABORTED: Save-to-drafts/Discard prompt appeared after Post` and stop. Do NOT auto-discard or auto-save.
23. **Emit the success marker** as the final line: `UPLOAD_VIDEO_POSTED: ${VIDEO_URL}`. This is the only signal the caller uses to mark the Feishu record as posted. Without this marker, the caller treats the run as a silent abort and writes a failure note instead.
