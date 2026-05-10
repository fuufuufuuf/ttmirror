---
version: 1
name: Favorite TikTok Music
app: TikTok
ios_min: "17.0"
locale: "en_US"
tags: ["tiktok", "music", "favorite", "save", "sound"]
params:
  - name: MUSIC_URL
    description: "Full TikTok music URL, e.g. https://www.tiktok.com/music/Agora-Hills-7281750433272580907"
    required: true
---

Save (favorite) a TikTok sound/music to the current account's saved sounds. The URL is opened via Spotlight, which usually deep-links straight into the TikTok app; if it routes through Safari instead, the in-page "Open TikTok" handoff is used as a fallback.

## Rules

- **Image bandwidth**: every `screenshot` and every `describe_screen` (without `omit_screenshot: true`) sends a ~400KB image to the model and adds ~500ms-1s per call. Pass `omit_screenshot: true` whenever you only need OCR text / coordinates (the typical "find element to tap" case). Reserve full images for steps that explicitly call out **visual analysis** below. Never call `screenshot` immediately after `describe_screen` — describe_screen's default response already includes the same frame.

## Steps

### Part 0: Ensure iPhone Mirroring is active

1. Call `status` to check if mirroring is active
2. If not active, call `screenshot` to wake up the session, then call `status` again
3. If still not active, report an error and stop

### Part 1: Open the music URL via Spotlight

4. Press **Cmd+3** to open Spotlight. The search field is auto-focused — **do NOT tap it** (the tap is unreliable and unnecessary). Clean any stale text: press **Cmd+A** to select all, then **Delete** to clear (no-op if already empty).
5. Type the URL directly with `type_text` `${MUSIC_URL}`. Do **not** use `pbcopy` + Cmd+V — Universal Clipboard does not sync from script-driven `pbcopy` to iOS via iPhone Mirroring, so Cmd+V will paste a stale value.
6. Press **Return** to open the URL. This triggers iOS's universal-link handoff, which deep-links the TikTok URL straight into the TikTok app.

### Part 2: Hand off to TikTok app (fallback — only if Safari opened instead)

7. Call `describe_screen` (with default `omit_screenshot: false` — visual analysis required: state detection between "TikTok app already showing" vs "Safari popup" relies on the image; the response gives both OCR text and image in one call). Do NOT call `screenshot` separately afterward.
    - If the TikTok music page is already showing (with "Add to Apple Music" / "Save" / "Saved" button visible) → **skip to Part 3**.
    - If Safari is showing **any popup with an "Open TikTok" / "Open" button** (text variants: "Check out more sounds on TikTok", "Open this link in TikTok?", or just "Open TikTok" alone) → continue below.
8. **CRITICAL — DO NOT dismiss the popup.** Specifically:
   - **DO NOT** tap `Not now`, `Cancel`, `Close`, the `×` close icon, the dimmed background, or anywhere outside the popup.
   - **DO NOT** decide the URL is wrong and try to retype it — the popup IS the deep-link handoff for the correct URL.
   - The ONLY correct action is to tap the **"Open TikTok"** (or just **"Open"**) button on the popup.
9. From the same Step-7 response, tap the `"Open TikTok"` / `"Open"` button (use the uid / coords already in hand — no need to call `describe_screen` again).
10. Wait 3 seconds for TikTok to launch and navigate to the music page. `describe_screen` `omit_screenshot: true` to confirm you are now in the TikTok app on the music page (look for "Save" / "Saved" / "Add to Apple Music" text in the OCR result).

### Part 3: Save the music

11. Use `describe_screen` `omit_screenshot: true` on the TikTok music page. Look for the **"Save"** button (with a bookmark icon).
12. **If the button already shows "Saved"** (black filled bookmark): re-save it — tap once to unsave (button becomes "Save"), wait 2 seconds, then tap again to save (button becomes "Saved"). This refreshes the save timestamp.
13. **If the button shows "Save"**: tap it once.
14. Wait 2 seconds.

### Part 4: Verify

15. Use `describe_screen` `omit_screenshot: true` to confirm the button text changed to **"Saved"**.
16. If the button still shows "Save", report the failure.

### Part 5: Exit the music page

17. Tap the back arrow ("<") at fixed coordinates **(25, 93)** to exit the music page.
