# TikTok Mirror 自动化项目

## 坐标系统（核心）

- **禁止从截图估算坐标**：不要通过 `screenshot` 的图片像素位置来推算 tap 坐标，错误率极高
- **MUST 使用 `describe_screen`** 获取 tap 坐标，其返回的坐标可以直接用于 `tap`
- `screenshot` 仅用于：唤醒 mirroring、确认操作结果、视觉验证。**绝不用于定位点击目标**

## Skills

项目自定义的 mirroir skills 存放在 `skills/` 目录下：
- `skills/safari/` — Safari 相关操作以及tiktok操作（下载视频、保存到相册）
- `skills/tiktok/` — TikTok 相关操作（切换账号等）

支持 `${VAR}` 环境变量替换。

**加载优先级**：项目本地 `.mirroir-mcp/skills/` > 全局 `~/.mirroir-mcp/skills/`

## Camera Dialog Workaround

When TikTok accesses the camera via iPhone Mirroring, a system dialog "iPhone camera is not available from Mac" appears and pauses mirroring. All mirroir MCP tools will fail with "Target 'iphone' is paused".

**Fix**: Run `./dismiss_camera_dialog.sh` — it screenshots the window, uses Swift Vision OCR to find the OK button, and clicks it via `cliclick`.
