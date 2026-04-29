---
version: 1
name: Kill an app on iPhone (force-quit)
app: any
ios_min: "17.0"
locale: "any"
tags: ["ios", "iphone", "app-switcher", "kill", "force-quit"]
params:
  - name: APP_NAME
    description: "Display name of the app to kill, as it appears in Spotlight (e.g. 'OpenVPN', 'TikTok', 'Chrome')"
    required: true
---

Force-quit any iPhone app via iPhone Mirroring. Strategy: launch the app first so it becomes the most recent, open the App Switcher, find its card, and dismiss it with a deliberate slow drag.

## Why not `mcp__mirroir__reset_app`

The built-in `reset_app` helper invokes Spotlight internally and intermittently fails with `"Failed to open Spotlight. Is target 'iphone' running?"` in some macOS / mirroir builds (observed on Darwin 25.3 + mirroir 0.33). This skill uses raw `press_key` calls which are reliable.

## Rules

- The dismiss gesture **must use `drag` (not `swipe`)** with `from_y ≥ 500` and `duration_ms ≥ 1000`. Shorter / faster gestures get intercepted by iPhone Mirroring and become a scroll, not a card dismiss.
- After `Cmd+2`, the **most-recent app card is NOT always centered** in iPhone Mirroring (unlike on the physical device). It may be the right-side partial card. Locate it visually first; do NOT assume center coordinates.

## Steps

### Part 1: Launch the target app (so it lands in App Switcher)

1. `press_key` `command+3` to open Spotlight.
2. `type_text` `${APP_NAME}`.
3. `press_key` `return` to launch the top hit.
4. Wait ~2 seconds for the app to actually load (use `Bash sleep 2` or screenshot-poll).

### Part 2: Open App Switcher and locate the card

5. `press_key` `command+2` to open the App Switcher.
6. `screenshot`. Identify which visible card belongs to `${APP_NAME}` by looking at the icon / title strip above each card. The target may be:
   - centered (typical x ≈ 167 on a 334-wide window),
   - or the right-side partial card (x ≈ 290),
   - or the left-side partial card (x ≈ 40).

### Part 3: Dismiss the card

7. `drag` from `(x, 500)` to `(x, 0)` over `1000` ms — where `x` is the card center x from Step 6.
8. `screenshot` to confirm: the card identified in Step 6 should no longer be visible.
9. If the card is still there: take a fresh `screenshot`, re-identify x (the layout may have shifted after sibling cards moved), and retry Step 7. Do not retry more than 2 times.

### Part 4: Return to home

10. `press_key` `command+1` to leave the App Switcher and return to the Home Screen.
