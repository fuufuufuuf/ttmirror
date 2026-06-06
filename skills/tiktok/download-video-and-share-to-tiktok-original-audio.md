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
5. Open a new tab with **Cmd+T**.
6. Press **Cmd+L** to focus the address bar, then press **Cmd+A** + **Delete** to clear any stale text in the address bar (no-op if already empty).
7. Type the URL directly with `type_text` `${VIDEO_URL}`, then `press_key` using `key: "return"` to navigate. Do **not** use `pbcopy` + Cmd+V — Universal Clipboard does not sync from script-driven `pbcopy` to iOS via iPhone Mirroring, so Cmd+V will paste a stale value. Wait for the page to load, then `describe_screen` `omit_screenshot: true` to verify: the address bar host is the expected domain (e.g. `res.cloudinary.com`) and expected content is visible (e.g. a `DOWNLOAD` button + `<filename>.mp4 (<size>)`).

### Part 2: Share video to TikTok

8. Tap "DOWNLOAD" — **critical button, OCR mis-locates Y by ~25-30px** (cloudinary's page renders the filename `<name>.mp4 (<size>)` and the blue DOWNLOAD button as one composite element; OCR returns the composite's center, which lands above the actual button). Always cross-validate against the image:
    a. `describe_screen` `omit_screenshot: false`. Read the OCR coords for "DOWNLOAD" → candidate `(x1, y1)`. Visually check the image: does `(x1, y1)` fall inside the visible blue DOWNLOAD button rectangle?
        - **Yes** → tap `(x1, y1)`.
        - **No** → estimate visual coords `(x2, y2)` from the button's visible center and tap `(x2, y2)`.
    b. Wait ~2s for the "Download complete" banner at the bottom of the screen.
    c. If the banner does NOT appear, the tap missed. Do **not** retry the same coordinates. Re-do (a) with **visual coordinates only** — read the button center from the image and ignore any OCR-returned Y. Retry up to 2 more times.
    d. Only proceed once the "Download complete" banner is visible.
9. Tap "OPEN IN..." on the download complete banner to open the share sheet
10. Wait for the share sheet to appear
11. Use `describe_screen` `omit_screenshot: true` to check if "TikTok" is in the app icon row. If not visible, swipe the row with `mcp__mirroir__swipe(from_x=50, to_x=300, duration_ms=1000)` — a single swipe of this magnitude typically jumps to the end of the row where TikTok lives. **Never** call it in the reverse direction (e.g. `from_x=200, to_x=50`): empirically, short leftward swipes are silently dropped by mirroir; only low-to-high X reliably advances the row. After each swipe, `describe_screen` `omit_screenshot: true` to verify. Repeat the same call (not the reverse) until "TikTok" appears, then tap it.
12. Wait for TikTok to open. A "Share on TikTok" modal appears with **Video** and **Message** buttons. Use `describe_screen` `omit_screenshot: true` to locate the "Video" button, then tap it to enter the video editing flow.

### Part 3: Go directly to Next

The fallback path does NOT touch any audio UI at all. Whatever audio state the editor lands in (original audio, or a default-attached song if TikTok auto-attached one) is accepted as-is. Do NOT do anything besides tapping Next:

- Do NOT tap `Add sound` / `/ Add sound` at the top center (~`(167, 113)`). Do not open the sound picker at all.
- Do NOT tap any `♪ <song> ×` chip at the top of the editor. Leave any auto-attached default song chip alone.
- Do NOT tap the Original mic icon at the bottom-left toolbar (~`(62, 691)`).
- Do NOT open Favorites / Hot / For You / Recent.

13. Tap **Next**. Wait for the post editing screen (caption, hashtags).

### Part 4: Add description (no product) and Post

15. Tap the "Add description..." text field. If `VIDEO_TITLE` is non-empty, type it directly with `type_text` `${VIDEO_TITLE}`. If empty, leave the description blank and proceed. Do **not** use `pbcopy` + Cmd+V (Universal Clipboard does not sync reliably under iPhone Mirroring).
16. **Skip** the "Add link → Product → showcase → Add" flow. This skill must NOT add any product link to the post.
17. Use `describe_screen` `omit_screenshot: true` to locate the red **Post** button at the bottom-right of the post editor (label `"Post"` or `"+ Post"`; on a 334x735 mirroring window it sits near `(246, 679)` — but ALWAYS confirm via OCR before tapping, this is the destructive publish action).
18. Tap Post.
19. Wait until the post editor is **gone** — the screen transitions to the TikTok feed / profile (or shows a "Posted" / "Uploading..." indicator briefly). Verify via `describe_screen` `omit_screenshot: true`: the `"Add description..."` field and the `"Drafts"` / `"Post"` buttons must NOT be visible anymore.
20. If a "Save to drafts?" / "Discard?" prompt appears instead of a successful publish, the post failed — emit `UPLOAD_VIDEO_ABORTED: Save-to-drafts/Discard prompt appeared after Post` and stop. Do NOT auto-discard or auto-save.
21. **Emit the success marker** as the final line: `UPLOAD_VIDEO_POSTED: ${VIDEO_URL}`. This is the only signal the caller uses to mark the Feishu record as posted. Without this marker, the caller treats the run as a silent abort and writes a failure note instead.
