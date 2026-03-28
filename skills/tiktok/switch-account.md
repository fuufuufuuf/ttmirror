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

- **Coordinates**: **MUST** use `describe_screen` to get tap coordinates — never estimate from screenshot pixels. `describe_screen` returns coordinates that can be used directly with `tap`. `screenshot` is only for visual verification, not for locating tap targets.
- **Pacing**: Wait **2 seconds** (`sleep 2`) between consecutive mirroir tool calls to avoid rate limits. Only use `describe_screen` when you need to find a tap target.
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
5. Press **Cmd+3** to open Spotlight Search
6. Tap the search field at the bottom, type "tiktok" and press **Return** to launch TikTok
7. Wait for TikTok to load

### Part 2: Go to Profile and check current account

8. Use `describe_screen` to locate the **Profile** tab — look for an element labeled "Profile" in the bottom navigation bar. The `describe_screen` coordinates point to the text label, which is above the actual tappable icon. Add **55 points** to the Y coordinate returned by `describe_screen` before tapping (e.g. if `describe_screen` returns y=645, tap at y=700).
9. Wait for the Profile page to load
10. Use `describe_screen` to read the current username displayed on the Profile page (shown as "Username v" with a dropdown arrow, and "@username" below it)
11. **Compare** the displayed username (case-insensitive) with `${ACCOUNT_USERNAME}`:
   - If they match, the correct account is already active. Take a screenshot as confirmation and **stop here** — no switch needed.
   - If they do not match, continue to Part 3.

### Part 3: Open account switcher

12. Tap the username text (the one with the dropdown arrow "v") to open the "Switch account" bottom sheet
13. Wait for the account switcher to appear

### Part 4: Find and select the target account

14. Use `describe_screen` to read all accounts listed in the switcher
15. Look for `${ACCOUNT_USERNAME}` in the list (case-insensitive match)
16. If the account is not visible, swipe up in the account list to reveal more accounts, then `describe_screen` again. Repeat until found or the list is exhausted
17. If the account is not found at all, close the switcher (tap the **x** button) and report an error: "Account '${ACCOUNT_USERNAME}' not found in the account switcher"
18. Tap the target account name to switch

### Part 5: Verify the switch

19. Wait 3 seconds for the account switch to complete
20. Use `describe_screen` on the Profile page
21. Confirm the displayed username matches `${ACCOUNT_USERNAME}`. If it matches, the switch is successful. If not, report the mismatch.
22. Take a screenshot as confirmation: "tiktok_account_switched"
