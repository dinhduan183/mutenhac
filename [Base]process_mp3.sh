#!/bin/zsh

cd "$(dirname "$0")"

for f in *.mp3; do
  [ -e "$f" ] || continue

  filename="${f:r}"
  output="${filename}_3unmute-8mute.mp3"

  echo "Đang xử lý: $f"

  ffmpeg -y -i "$f" \
    -af "volume=enable='gte(mod(t,11),3)':volume=0" \
    "$output"

  echo "Xong: $output"
done

echo "Hoàn tất tất cả file mp3!"
read -p "Nhấn Enter để thoát..."