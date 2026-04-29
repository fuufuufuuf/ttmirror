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

- **Coordinates**: **MUST** use `describe_screen` to get tap coordinates — never estimate from screenshot pixels. `screenshot` is only for visual verification, not for locating tap targets.
- **Failure recovery**: If any step fails or the UI is not in the expected state, **do NOT try alternative approaches, workarounds, or ad-hoc recovery**. Force-quit the foreground app (App Switcher) and restart from **Step 1**.
- **Keyboard shortcut** (iPhone Mirroring): **Cmd+3** opens Spotlight Search.

## Steps

### Part 0: Ensure iPhone Mirroring is active

1. Call `status` to check if mirroring is active
2. If not active, call `screenshot` to wake up the session, then call `status` again
3. If still not active, report an error and stop

### Part 1: Open the music URL via Spotlight

4. Press **Cmd+3** to open Spotlight (search box is auto-focused, no need to tap it)
5. Copy the URL to macOS clipboard: run `echo -n "${MUSIC_URL}" | pbcopy`, then paste with **Cmd+V** (preserves exact casing).
6. Press **Return**
7. Wait 3 seconds. Spotlight typically deep-links the TikTok URL straight into the TikTok app.

### Part 2: Hand off to TikTok app (fallback — only if Safari opened instead)

8. `describe_screen` to check what's on screen.
    - If the TikTok music page is already showing (with "Add to Apple Music" / "Save" / "Saved" button visible) → **skip to Part 3**.
    - If Safari is showing with a "Check out more sounds on TikTok" popup → continue below.
9. Find the **"Open"** / **"Open TikTok"** button on the in-page popup
10. Tap the button
11. Wait 3 seconds for TikTok to launch and navigate to the music page

### Part 3: Save the music

12. Use `describe_screen` on the TikTok music page. Look for the **"Save"** button (with a bookmark icon)
13. **If the button already shows "Saved"** (black filled bookmark): re-save it — tap once to unsave (button becomes "Save"), wait 2 seconds, then tap again to save (button becomes "Saved"). This refreshes the save timestamp.
14. **If the button shows "Save"**: tap it once.
15. Wait 2 seconds.

### Part 4: Verify

16. Use `describe_screen` to confirm the button text changed to **"Saved"**.
17. If verified, take a screenshot: "tiktok_music_saved".
18. If the button still shows "Save", report the failure.

### Part 5: Exit the music page

19. Tap the back arrow ("<") at fixed coordinates **(25, 93)** to exit the music page.
