---
version: 1
name: Switch TikTok Account
app: TikTok
ios_min: "17.0"
locale: "en_US"
tags: ["tiktok", "account", "switch", "profile"]
params:
  - name: ACCOUNT_USERNAME
    description: "The TikTok username to switch to (without @ prefix, e.g. dsolores)"
    required: true
---

Switch to a specific TikTok account by username. The target account must already be logged in (visible in the account switcher). If the current account already matches, no switch is performed.

## Rules

- **Coordinates**: **MUST** use `describe_screen` to get tap coordinates — never estimate from screenshot pixels. `screenshot` is only for visual verification, not for locating tap targets.
- **Image bandwidth**: every `screenshot` and every `describe_screen` (without `omit_screenshot: true`) sends a ~400KB image to the model and adds ~500ms-1s per call. Pass `omit_screenshot: true` whenever you only need OCR text / coordinates (the typical "find element to tap" case). Reserve full images for steps that explicitly call out **visual analysis** below (icon color, etc.). Never call `screenshot` immediately after `describe_screen` — describe_screen's default response already includes the same frame.
- **Failure recovery**: If any step fails or the UI is not in the expected state, **do NOT try alternative approaches, workarounds, or ad-hoc recovery**. Immediately kill TikTok (force-quit via App Switcher or `killall` equivalent) and restart the entire skill from **Step 1**.
- **Fixed coordinates**:
  - **Profile** tab: **(300, 680)**
- **Keyboard shortcuts** (iPhone Mirroring):
  - **Cmd+1**: Home Screen
  - **Cmd+2**: App Switcher
  - **Cmd+3**: Spotlight Search

## Steps

### Part 0: Ensure iPhone Mirroring is active

1. Call `status` to check if mirroring is active
2. If the status is **not** active (e.g. paused or no window), call `screenshot` to wake up the mirroring session, then call `status` again to confirm it is now active
3. If still not active after retry, report an error and stop

### Part 1: Launch TikTok

4. Press **Cmd+1** to go to the Home Screen
5. Press **Cmd+3** to open Spotlight Search. The search field is auto-focused — **do NOT tap it** (the tap is unreliable and unnecessary).
6. `type_text` `tiktok` directly, then press **Return** to launch TikTok.
7. Wait for TikTok to load

### Part 2: Go to Profile and check current account


8. **Precondition** — verify TikTok loaded correctly: use `describe_screen` `omit_screenshot: true` to check that the bottom tab bar contains a **Profile** icon/label. If the Profile icon is **not** present (TikTok may not have loaded, may be showing a login wall, an interstitial, or a different screen), do not attempt to tap — kill TikTok and restart from Step 1.

   Once Profile is confirmed visible, tap **Profile** at fixed coordinates **(300, 680)**. Then use `describe_screen` (with default `omit_screenshot: false` — visual analysis required: judging Profile icon "black/filled" vs highlight color cannot be done from OCR text alone) to check the bottom tab bar — if the **Profile** icon is **black** (filled) and the bottom bar highlight color is **white**, the tap succeeded and you are on the Profile page. If not, retry the tap until the Profile page is confirmed.
9. If the username is not visible (e.g. the page is scrolled down showing the video grid), tap the status bar at **(47, 57)** to scroll the page back to the top (iOS native behavior).
10. Use `describe_screen` `omit_screenshot: true` to read the current username displayed on the Profile page (shown as "@username")
11. **Compare** the displayed username (case-insensitive) with `${ACCOUNT_USERNAME}`:
    - If they match, the correct account is already active — **stop here** — no switch needed.
    - If they do not match, continue to Part 3.

### Part 3: Open account switcher

12. Tap fixed coordinates **(167, 196)** to open the "Switch account" bottom sheet.

### Part 4: Find and select the target account

13. Use `describe_screen` `omit_screenshot: true` to read all accounts listed in the switcher
14. Look for `${ACCOUNT_USERNAME}` in the list (case-insensitive match)
15. If the account is not visible, scroll down in the account list to reveal more accounts, then `describe_screen` `omit_screenshot: true` again. Repeat until found or the list is exhausted
16. If the account is not found at all, close the switcher (tap the **x** button) and report an error: "Account '${ACCOUNT_USERNAME}' not found in the account switcher"
17. Tap the target account name to switch

### Part 5: Verify the switch

18. Wait 3 seconds for the account switch to complete
19. Use `describe_screen` `omit_screenshot: true` on the Profile page
20. Confirm the displayed username matches `${ACCOUNT_USERNAME}`. If it matches, the switch is successful. If not, report the mismatch.
