# TikTok Mirror Automation Project

## Coordinate System (Core)

Every `tap` operation MUST strictly follow this procedure:

### Step 1: Get candidate coordinates
- Call `describe_screen` to retrieve the element list
- Find the target element in the list; record its coordinates as the candidate `(x1, y1)`
- If the target is not in the list (not even as an anonymous "icon"), skip to Step 4

### Step 2: Cross-validate with a screenshot
- Call `screenshot` to capture the current screen
- Check whether `(x1, y1)` falls inside the visual bounds of the target element in the screenshot
- **Match** → execute `tap(x1, y1)`, then go to Step 5
- **Mismatch** → go to Step 3

### Step 3: Use visual coordinates from the screenshot
- Estimate coordinates `(x2, y2)` from the target's visual position in the screenshot
- Execute `tap(x2, y2)`, then go to Step 5

### Step 4: Fallback when the element is completely unrecognized
- `describe_screen` did not return the target element (not even as an anonymous icon)
- Estimate visual coordinates `(x3, y3)` directly from the `screenshot`
- Execute `tap(x3, y3)`, then go to Step 5

### Step 5: Verify the result
- Call `screenshot` to confirm the UI changed as expected
- **If the tap had no effect**: do NOT retry with the same coordinates. You MUST go back to Step 1 and call `describe_screen` again to get fresh coordinates.

### When Step 2 (cross-validation) is most critical
- Small icons near the screen edges (X close buttons, back arrows, etc.)
- Critical or irreversible action buttons (publish, delete, share, pay, etc.)
- Densely packed UI (list items, toolbars) where you could easily hit a neighboring element

## Skills

Project-specific mirroir skills live under `skills/`:
- `skills/safari/` — Safari operations and TikTok operations (download videos, save to Photos)
- `skills/tiktok/` — TikTok operations (account switching, etc.)

`${VAR}` environment variable substitution is supported.

**Load priority**: project-local `.mirroir-mcp/skills/` > global `~/.mirroir-mcp/skills/`

## Camera Dialog Workaround

When TikTok accesses the camera via iPhone Mirroring, a system dialog "iPhone camera is not available from Mac" appears and pauses mirroring. All mirroir MCP tools will fail with "Target 'iphone' is paused".

**Fix**: Run `./dismiss_camera_dialog.sh` — it screenshots the window, uses Swift Vision OCR to find the OK button, and clicks it via `cliclick`.
