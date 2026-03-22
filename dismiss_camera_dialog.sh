#!/bin/bash
# Dismiss the "iPhone camera is not available from Mac" dialog on iPhone Mirroring.
# Usage: ./dismiss_camera_dialog.sh
#
# When mirroring is paused by the camera dialog:
# 1. Activate window and click to resume mirroring
# 2. Take a screenshot of the window and OCR to find OK button
# 3. Click the OK button via cliclick (bypasses MCP pause issue)
#
# Requires: cliclick, swift (macOS built-in)

set -e

TMPDIR_PATH=$(mktemp -d)
SCREENSHOT="$TMPDIR_PATH/mirroring.png"
OCR_SWIFT="$TMPDIR_PATH/ocr.swift"

cleanup() {
    rm -rf "$TMPDIR_PATH"
}
trap cleanup EXIT

# Step 1: Get window info and activate
WIN_POS=$(osascript -e '
    tell application "iPhone Mirroring" to activate
    delay 0.3
    tell application "System Events"
        tell process "iPhone Mirroring"
            set winPos to position of window 1
            set winSize to size of window 1
            return (item 1 of winPos) & "," & (item 2 of winPos) & "," & (item 1 of winSize) & "," & (item 2 of winSize)
        end tell
    end tell
' 2>/dev/null)

WIN_X=$(echo "$WIN_POS" | cut -d',' -f1 | tr -d ' ')
WIN_Y=$(echo "$WIN_POS" | cut -d',' -f2 | tr -d ' ')
WIN_W=$(echo "$WIN_POS" | cut -d',' -f3 | tr -d ' ')
WIN_H=$(echo "$WIN_POS" | cut -d',' -f4 | tr -d ' ')

echo "Window at ($WIN_X, $WIN_Y) size ${WIN_W}x${WIN_H}"

# Step 2: Screenshot the window
WIN_ID=$(osascript -e '
    tell application "iPhone Mirroring"
        return id of window 1
    end tell
' 2>/dev/null)

screencapture -l"$WIN_ID" -o -x "$SCREENSHOT" 2>/dev/null

if [ ! -f "$SCREENSHOT" ]; then
    echo "Error: Failed to capture screenshot"
    exit 1
fi

# Step 3: OCR with Swift Vision framework to find OK button
cat > "$OCR_SWIFT" << 'SWIFT'
import Vision
import Foundation
import CoreGraphics
import ImageIO

let args = CommandLine.arguments
guard args.count > 1 else {
    fputs("Usage: ocr <image_path>\n", stderr)
    exit(1)
}

let url = URL(fileURLWithPath: args[1])
guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
      let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
    fputs("Failed to load image\n", stderr)
    exit(1)
}

let imgW = CGFloat(image.width)
let imgH = CGFloat(image.height)

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate

let handler = VNImageRequestHandler(cgImage: image)
try! handler.perform([request])

guard let results = request.results else { exit(1) }

for obs in results {
    guard let candidate = obs.topCandidates(1).first else { continue }
    let text = candidate.string.trimmingCharacters(in: .whitespaces)
    if text == "OK" {
        let box = obs.boundingBox
        let cx = (box.origin.x + box.size.width / 2) * imgW
        let cy = (1 - box.origin.y - box.size.height / 2) * imgH
        print("\(Int(cx)),\(Int(cy)),\(Int(imgW)),\(Int(imgH))")
        exit(0)
    }
}

fputs("OK button not found\n", stderr)
exit(1)
SWIFT

OK_POS=$(swift "$OCR_SWIFT" "$SCREENSHOT" 2>/dev/null)

if [ -z "$OK_POS" ]; then
    echo "OK button not found — dialog may not be present"
    exit 0
fi

IMG_OK_X=$(echo "$OK_POS" | cut -d',' -f1)
IMG_OK_Y=$(echo "$OK_POS" | cut -d',' -f2)
IMG_W=$(echo "$OK_POS" | cut -d',' -f3)
IMG_H=$(echo "$OK_POS" | cut -d',' -f4)

echo "OCR found OK at pixel ($IMG_OK_X, $IMG_OK_Y) in ${IMG_W}x${IMG_H} image"

# Step 4: Convert to screen coordinates and click
SCALE_X=$(python3 -c "print(${IMG_W} / ${WIN_W})")
SCALE_Y=$(python3 -c "print(${IMG_H} / ${WIN_H})")
CLICK_X=$(python3 -c "print(int(${WIN_X} + ${IMG_OK_X} / ${SCALE_X}))")
CLICK_Y=$(python3 -c "print(int(${WIN_Y} + ${IMG_OK_Y} / ${SCALE_Y}))")

echo "Clicking OK at screen position ($CLICK_X, $CLICK_Y)"
cliclick c:"$CLICK_X","$CLICK_Y"
echo "Done."
