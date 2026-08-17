# Mute Nhạc

App desktop tự động bật/tắt tiếng file nhạc và video theo chu kỳ, dùng `ffmpeg`. Mặc định: **3 giây bật tiếng — 8 giây tắt tiếng**, lặp lại đến hết bài.

Viết bằng Python + Tkinter, chạy được trên macOS và Windows.

## Tính năng

- Chọn nhiều file một lúc, hoặc quét cả thư mục
- Hỗ trợ audio (`.mp3 .wav .m4a .aac .flac .ogg .opus`) và video (`.mp4 .mov .mkv .avi .m4v .webm .flv .wmv`)
- Với video: xuất 1 video đã xử lý tiếng (giữ nguyên hình, không encode lại) + tách riêng 1 file mp3 âm thanh gốc
- Tự chỉnh số giây bật/tắt, có dải sóng minh hoạ chu kỳ realtime
- Hậu tố tên file tự sinh theo thông số (`_3s-on-8s-off`), sửa tay được
- Chọn thư mục lưu riêng hoặc để cùng chỗ file gốc
- Thanh tiến trình, log realtime có màu, nút Huỷ giữa chừng
- Xử lý chạy nền, giao diện không bị đơ

## Yêu cầu

- **Python 3.10+** (có sẵn `tkinter`)
- **ffmpeg**
  - macOS: `brew install ffmpeg`
  - Windows: tải tại <https://www.gyan.dev/ffmpeg/builds/>, thêm vào PATH hoặc đặt `ffmpeg.exe` cạnh `mute_app.py`

App tự tìm ffmpeg theo thứ tự: bản nhúng trong bundle → PATH → các đường dẫn phổ biến (`/opt/homebrew/bin`, `/usr/local/bin`, `C:\ffmpeg\bin`…). Trạng thái hiện ở góc phải header.

## Chạy trực tiếp (không cần build)

```bash
python3 mute_app.py
```

## Build

### macOS — `dist/MuteNhac.app`

```bash
bash build_mac.sh
```

Script sẽ tạo `.venv`, cài `pyinstaller`, nhúng `icon.icns` làm icon app, nhúng luôn `ffmpeg` nếu máy đã cài (app chạy được trên máy chưa cài ffmpeg).

### Windows — `dist\MuteNhac.exe`

1. Cài Python từ <https://python.org> (tick **Add Python to PATH**)
2. Đặt `ffmpeg.exe` cạnh `mute_app.py` hoặc thêm vào PATH
3. Double-click `build_windows.bat`

## Cách dùng

1. **Chọn file…** (một hoặc nhiều) hoặc **Chọn thư mục…** (cả batch)
2. Chỉnh **Bật tiếng** / **Tắt tiếng** theo giây — mặc định 3 / 8
3. (Tuỳ chọn) đổi **Hậu tố tên file** và **Thư mục lưu**
4. Bấm **▶ Bắt đầu xử lý**

File ra:

| Đầu vào | Kết quả |
|---|---|
| `bai-hat.mp3` | `bai-hat_3s-on-8s-off.mp3` |
| `clip.mp4` | `clip_3s-on-8s-off.mp4` (đã xử lý tiếng) + `clip_goc.mp3` (âm thanh gốc) |

## Logic ffmpeg

```
volume=enable='gte(mod(t, cycle), unmute)':volume=0
```

`cycle = unmute + mute`. Trong mỗi chu kỳ, từ giây thứ `unmute` trở đi âm lượng về 0, phần trước đó giữ nguyên.

Video được xử lý với `-c:v copy` (không đụng vào hình) và `-c:a aac -b:a 192k`; file mp3 gốc tách bằng `-vn -c:a libmp3lame -q:a 2`.

## Khi gặp lỗi

- **"Không tìm thấy ffmpeg"** — cài theo hướng dẫn trên, hoặc đặt `ffmpeg` / `ffmpeg.exe` cạnh app
- **macOS báo "không xác minh được nhà phát triển"** — chuột phải vào app → Open → Open, hoặc System Settings → Privacy & Security → Open Anyway
- **Build lỗi `ValueError: invalid literal for int()` trong PyInstaller** — Python của Homebrew bị lệch `libexpat` khiến `platform.mac_ver()` trả rỗng. Sửa bằng:
  ```bash
  brew reinstall --build-from-source python@3.14
  ```
- **Icon không đổi sau khi build** — Finder cache: `killall Finder Dock`

## Cấu trúc

```
mute_app.py           mã nguồn app (UI + xử lý ffmpeg)
build_mac.sh          build .app cho macOS
build_windows.bat     build .exe cho Windows
MuteNhac.spec         spec PyInstaller (tự sinh khi build)
icon.icns / icon.png  icon app
[Base]process_mp3.sh  script bash gốc trước khi có GUI
HUONG_DAN.md          hướng dẫn bản cũ
```
