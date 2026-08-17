#!/bin/bash
# Build app desktop cho macOS bằng PyInstaller
# Yêu cầu: Python 3.10+, ffmpeg đã cài (brew install ffmpeg)
# Chạy: bash build_mac.sh

set -e
cd "$(dirname "$0")"

echo "==> Tạo virtual env"
python3 -m venv .venv
source .venv/bin/activate

echo "==> Cài PyInstaller"
pip install --upgrade pip
pip install pyinstaller

# Nhúng ffmpeg vào bundle nếu có (tuỳ chọn). Nếu không, app sẽ tìm ffmpeg trên PATH.
EXTRA_DATA=""
if command -v ffmpeg >/dev/null 2>&1; then
    FFMPEG_BIN="$(command -v ffmpeg)"
    echo "==> Phát hiện ffmpeg: $FFMPEG_BIN — sẽ nhúng vào bundle"
    EXTRA_DATA="--add-binary ${FFMPEG_BIN}:."
fi

# Icon app (icon.icns cạnh file này). Không có thì dùng icon mặc định của PyInstaller.
ICON_ARG=""
if [ -f "icon.icns" ]; then
    echo "==> Dùng icon: icon.icns"
    ICON_ARG="--icon icon.icns"
fi

echo "==> Build .app"
pyinstaller --noconfirm --windowed \
    --name "MuteNhac" \
    --osx-bundle-identifier "com.duan.mutenhac" \
    $ICON_ARG \
    $EXTRA_DATA \
    mute_app.py

echo
echo "==> Xong! App ở: dist/MuteNhac.app"
echo "    Mở bằng: open dist/MuteNhac.app"
