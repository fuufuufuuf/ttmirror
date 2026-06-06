# TikTok Mirror Automation Project

## Coordinate System

Every `tap` operation must follow this procedure:

1. Call `describe_screen` to retrieve the current element list.
2. Find the target element and record its returned coordinates as `(x1, y1)`.
3. Cross-check critical taps with the current image when the target is small, near an edge, destructive, or packed near other controls.
4. Tap only fresh coordinates from the current screen. Do not reuse old coordinates after a failed tap or screen transition.
5. Verify the result with `screenshot` or `describe_screen`. If the tap had no effect, return to step 1 and collect fresh coordinates.

## Project Skills

Project-specific automation instructions live under `skills/`:

- `skills/tiktok/`: TikTok operations such as upload, account switching, and music favoriting.
- `skills/chrome/`: TikTok Shop dashboard operations through the `chrome-devtools` MCP server.
- `skills/ios/`: cross-cutting iOS operations such as force-quitting apps.

The Python callers inject the relevant skill markdown into each Codex prompt. Treat the injected skill text as the source of truth for that run.

## Required Startup Context

Before performing project automation work, read every file under `skills/ios/`. These are shared iOS operations that other skills depend on.

## App Force-Quit Rule

Any time a skill or recovery path needs to force-quit, kill, reset, or restart an iPhone app, use `skills/ios/kill-app.md`.

Do not manually swipe or drag in the App Switcher to dismiss a card unless you are following that skill. Do not use `mcp__mirroir__reset_app`.

If a sub-skill says "force-quit via App Switcher", interpret it as invoking `skills/ios/kill-app.md` with `APP_NAME=<that app>`.

## Camera Dialog Workaround

When TikTok accesses the camera through iPhone Mirroring, macOS may show "iPhone camera is not available from Mac" and pause mirroring. Mirroir MCP tools can then fail with "Target 'iphone' is paused".

If this happens, use the project workaround script when appropriate:

```bash
./dismiss_camera_dialog.sh
```

After dismissing the dialog, verify mirroring is active before continuing.

## Completion Markers

Upload skills must emit exactly one final marker that the Python caller can parse:

- Success: `UPLOAD_VIDEO_POSTED: <video-url>`
- Abort: `UPLOAD_VIDEO_ABORTED: <one-line reason>`

Do not replace these markers with conversational text such as "please unlock the iPhone". The caller treats missing markers as a failed or silent upload.
