# Mute Nhạc - App Desktop

App GUI thay thế cho `process_mp3.sh`. Tự động xử lý MP3 theo chu kỳ unmute/mute (mặc định 3 giây nghe / 8 giây tắt) bằng `ffmpeg`.

## Tính năng

- Chọn nhiều file MP3 hoặc cả thư mục
- Tự chỉnh thời gian unmute / mute (giây)
- Tự đặt hậu tố tên file output, chọn thư mục lưu
- Thanh tiến trình + log realtime
- Có nút Huỷ giữa chừng
- Chạy đa luồng nên GUI không bị đơ

## Yêu cầu

- **Python 3.10+** (đã có sẵn `tkinter`)
- **ffmpeg** trên PATH
  - macOS: `brew install ffmpeg`
  - Windows: tải tại <https://www.gyan.dev/ffmpeg/builds/>, copy `ffmpeg.exe` cạnh `mute_app.py` hoặc thêm vào PATH

## Chạy thử nhanh (không cần build)

```bash
# Trong thư mục chứa mute_app.py
python3 mute_app.py        # macOS / Linux
python   mute_app.py        # Windows
```

## Build thành app desktop

### macOS — tạo `MuteNhac.app`

```bash
bash build_mac.sh
open dist/MuteNhac.app
```

Script sẽ:
1. Tạo virtualenv `.venv`
2. Cài `pyinstaller`
3. Nếu phát hiện `ffmpeg` đã cài, nhúng luôn vào bundle (app dùng được trên máy chưa cài ffmpeg)
4. Xuất ra `dist/MuteNhac.app`

> Nếu mở app báo "không xác minh được nhà phát triển": chuột phải vào app → Open → Open. Hoặc System Settings → Privacy & Security → Open Anyway.

### Windows — tạo `MuteNhac.exe`

1. Cài Python từ <https://python.org> (nhớ tick **Add Python to PATH**)
2. Tải `ffmpeg.exe`, copy cạnh `mute_app.py` (hoặc thêm vào PATH)
3. Double-click `build_windows.bat`
4. Chạy `dist\MuteNhac.exe`

## Cách dùng

1. Mở app → bấm **Chọn file…** (1 file) hoặc **Chọn thư mục…** (cả batch)
2. Chỉnh **Unmute** / **Mute** (giây) — mặc định là 3 / 8
3. (Tuỳ chọn) đổi **Thư mục lưu** và **Hậu tố tên file**
4. Bấm **▶ Bắt đầu xử lý**

File output có dạng `<tên gốc>_3unmute-8mute.mp3` ở cùng thư mục với file gốc (hoặc thư mục bạn chọn).

## Logic ffmpeg

App dùng đúng filter của script gốc:

```
volume=enable='gte(mod(t, cycle), unmute)':volume=0
```

`cycle = unmute + mute`. Mỗi chu kỳ, từ giây `unmute` trở đi sẽ bị tắt tiếng, các giây trước đó được giữ nguyên.

## Khi gặp lỗi

- *"Không tìm thấy ffmpeg"* → cài ffmpeg theo hướng dẫn ở trên, hoặc đặt `ffmpeg`/`ffmpeg.exe` cạnh app
- App không phản hồi khi xử lý file rất dài → kiểm tra log, có thể bấm **■ Huỷ**
- Trên macOS, app build ra không mở được → chuột phải → Open lần đầu để bypass Gatekeeper
