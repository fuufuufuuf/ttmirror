# TikTok Mirror 自动化项目

## Mirroir MCP 坐标系统

- 始终使用 `describe_screen` 获取精确的 tap 坐标，不要从截图猜测
- `describe_screen` 返回的坐标可以直接用于 `tap`
- 窗口大小单位是 points（如 334x735），不是像素
- 从截图估算坐标时，需要判断缩放比例：`tap坐标 = 截图像素坐标 / scale`
  - 比较截图图片分辨率与窗口 points 大小来确定 scale（如截图 668x1470 / 窗口 334x735 = 2x Retina）
  - 非 Retina 显示器 scale 为 1x，无需转换

## Skills

项目自定义的 mirroir skills 存放在 `skills/` 目录下：
- `skills/safari/` — Safari 相关操作（下载视频、保存到相册）
- `skills/tiktok/` — TikTok 相关操作（上传视频）

运行 `./setup.sh` 可将 skills 同步到 `~/.mirroir-mcp/skills/apps/`。

## Camera Dialog Workaround

When TikTok accesses the camera via iPhone Mirroring, a system dialog "iPhone camera is not available from Mac" appears and pauses mirroring. All mirroir MCP tools will fail with "Target 'iphone' is paused".

**Fix**: Run `./dismiss_camera_dialog.sh` — it screenshots the window, uses Swift Vision OCR to find the OK button, and clicks it via `cliclick`.
