#!/bin/bash
# Setup script: sync skills to ~/.mirroir-mcp/skills/apps/

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="$HOME/.mirroir-mcp/skills/apps"

for app_dir in "$SCRIPT_DIR/skills"/*/; do
    app_name=$(basename "$app_dir")
    mkdir -p "$TARGET_DIR/$app_name"
    cp -v "$app_dir"*.md "$TARGET_DIR/$app_name/"
done

echo "Skills synced to $TARGET_DIR"
