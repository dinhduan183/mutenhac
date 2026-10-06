# Mute Nhạc v2.5

App desktop xử lý tiếng của file nhạc và video theo chu kỳ, dùng `ffmpeg`. Mặc định: **3 giây bật tiếng, 8 giây tắt tiếng**, lặp lại đến hết bài.

Viết bằng Python + Tkinter, chạy được trên macOS và Windows.

## Tính năng

**Hai chế độ:**

| Chế độ | Đoạn tắt / đoạn chêm sẽ là |
|---|---|
| Bật/tắt tiếng → **Tắt hẳn** | im lặng hoàn toàn |
| Bật/tắt tiếng → **Chỉnh âm lượng** | bài gốc nhỏ đi theo mức dB (vd -30dB) |
| Chêm file phụ → **Tắt hẳn** | một đoạn file âm thanh phụ thay hẳn bài gốc ở đoạn đó |
| Chêm file phụ → **Chỉnh âm lượng** | file phụ phát đè lên, bài gốc vẫn chạy bên dưới ở mức dB đã chọn (vd -20dB) |

Với chế độ chêm file phụ: chọn file phụ, app hiện độ dài file, nhập số giây muốn lấy (tính từ đầu file phụ). Chu kỳ = đoạn bật + đoạn chêm. File ra dài bằng file gốc. File phụ có thể là mp3, wav, m4a… bất kỳ, không cần convert trước.

**Khác:**
- Chọn nhiều file một lúc hoặc cả thư mục
- Audio: `.mp3 .wav .m4a .aac .flac .ogg .opus` · Video: `.mp4 .mov .mkv .avi .m4v .webm .flv .wmv`
- Video: xuất 1 video đã xử lý tiếng (giữ nguyên hình, không encode lại) + 1 file mp3 âm thanh gốc
- Hậu tố tên file tự sinh theo thông số, sửa tay được
- Chọn thư mục lưu riêng hoặc để cùng chỗ file gốc
- Thanh tiến trình, nhật ký realtime, nút Huỷ
- Tự báo khi có bản mới: mở app lúc có mạng, nếu GitHub có release mới hơn sẽ hiện chip **"Có bản … — Tải về"** ở góc phải, bấm vào để mở trang tải

## Tải bản dựng sẵn

Vào trang [**Releases**](https://github.com/dinhduan183/mutenhac/releases/latest) tải:
- `MuteNhac-…-Windows.zip` → giải nén → chạy `MuteNhac.exe`
- `MuteNhac-…-macOS.zip` → giải nén → được `MuteNhac.app` (xem cách 1 bên dưới)

Cả hai đã nhúng sẵn ffmpeg, không cần cài thêm gì.

## Cài đặt trên macOS

### Cách 1 — Dùng app đã build sẵn

1. Tải `MuteNhac-…-macOS.zip` ở trang Releases, giải nén, kéo `MuteNhac.app` vào thư mục **Applications**.
2. Lần đầu mở: **chuột phải vào app → Open → Open** (app không ký bởi Apple nên macOS sẽ hỏi). Nếu vẫn bị chặn: **System Settings → Privacy & Security → Open Anyway**.

App đã nhúng sẵn ffmpeg, không cần cài gì thêm. Bản build sẵn chỉ chạy trên Mac chip Apple (M1 trở lên). Mac khác thì build lại theo cách 2.

### Cách 2 — Build từ mã nguồn

1. Cài [Homebrew](https://brew.sh) nếu chưa có:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
2. Cài Python, Tkinter và ffmpeg:
   ```bash
   brew install python python-tk ffmpeg
   ```
3. Tải mã nguồn và build:
   ```bash
   git clone https://github.com/dinhduan183/mutenhac.git
   cd mutenhac
   bash build_mac.sh
   ```
4. App nằm ở `dist/MuteNhac.app` — kéo vào Applications như cách 1.

Chỉ muốn chạy thử, không build: `python3 mute_app.py`.

## Cài đặt trên Windows

Cần 3 file đặt chung một thư mục: `mute_app.py`, `build_windows.bat`, `icon.ico`, và thêm `ffmpeg.exe`.

1. **Cài Python** từ <https://www.python.org/downloads/> (bản 3.10 trở lên). Ở màn hình cài đầu tiên **tick "Add python.exe to PATH"**, rồi bấm Install Now (giữ mặc định để có sẵn Tkinter).
2. **Lấy ffmpeg.exe**: tải `ffmpeg-release-essentials.zip` tại <https://www.gyan.dev/ffmpeg/builds/>, giải nén, lấy file `bin\ffmpeg.exe` bỏ vào cùng thư mục với `mute_app.py`.
3. **Double-click `build_windows.bat`**. Chờ vài phút đến khi hiện `Xong! App o: dist\MuteNhac.exe`.
4. Chạy `dist\MuteNhac.exe`. File exe đã nhúng sẵn ffmpeg, có thể copy đi máy Windows khác dùng luôn.

Chỉ muốn chạy thử, không build: mở CMD trong thư mục rồi gõ `python mute_app.py`.

Nếu Windows Defender / SmartScreen chặn exe: bấm **More info → Run anyway**.

## Phát hành phiên bản mới

1. Đổi `APP_VERSION` trong `mute_app.py`, commit và push.
2. Gắn tag rồi đẩy lên:
   ```bash
   git tag v2.5
   git push origin v2.5
   ```
3. GitHub Actions tự build bản Windows + macOS và đính vào Release (khoảng 2–3 phút). Theo dõi ở tab **Actions**.

## Cách dùng

1. **Chọn file…** hoặc **Chọn thư mục…**
2. Chọn chế độ:
   - **Bật/tắt tiếng**: nhập *Đoạn bật* / *Đoạn tắt* (giây), ở *Nhạc gốc ở đoạn tắt* chọn *Tắt hẳn* hoặc *Chỉnh âm lượng* + mức dB
   - **Chêm file phụ**: bấm *Chọn file phụ…*, nhập *Đoạn bật* (khoảng hát) và *Đoạn chêm* (giây), ở *Nhạc gốc ở đoạn chêm* chọn *Tắt hẳn* hoặc *Chỉnh âm lượng* + mức dB
3. (Tuỳ chọn) đổi **Hậu tố tên file** và **Thư mục lưu**
4. Bấm **▶ Bắt đầu xử lý**

| Đầu vào | Kết quả (vd) |
|---|---|
| `bai-hat.mp3` | `bai-hat_3s-on-8s-off.mp3` · `bai-hat_3s-on-8s-giam30dB.mp3` · `bai-hat_3s-on-5s-chen.mp3` · `bai-hat_3s-on-5s-chen-giam20dB.mp3` |
| `clip.mp4` | `clip_3s-on-8s-off.mp4` (đã xử lý tiếng) + `clip_goc.mp3` (âm thanh gốc) |

## Logic ffmpeg

Tắt tiếng / giảm âm lượng (`cycle = bật + tắt`, `level` = `0` hoặc `-30dB`):

```
volume=enable='gte(mod(t,cycle),unmute)':volume=level
```

Chêm file phụ: bài gốc bị tắt tiếng như trên; file phụ được cắt còn N giây, đệm im lặng `unmute` giây ở đầu, lặp liên tục theo chu kỳ rồi trộn (`amix`) đè lên bài gốc.

Video giữ hình bằng `-c:v copy`, tiếng xuất `-c:a aac -b:a 192k`; mp3 gốc tách bằng `-vn -c:a libmp3lame -q:a 2`.

## Khi gặp lỗi

- **"Không tìm thấy ffmpeg"** — Mac: `brew install ffmpeg`. Windows: đặt `ffmpeg.exe` cạnh `mute_app.py` rồi build lại.
- **Mac: "No module named '_tkinter'"** — `brew install python-tk`.
- **Mac: build lỗi `ValueError: invalid literal for int()` trong PyInstaller** — Python của Homebrew bị lệch `libexpat`: `brew reinstall --build-from-source python@3.14`.
- **Windows: `'python' is not recognized`** — cài lại Python và nhớ tick *Add python.exe to PATH*.
- **Icon không đổi sau khi build** — Mac: `killall Finder Dock`. Windows: `ie4uinit.exe -show`.

## Cấu trúc

```
mute_app.py         mã nguồn app (giao diện + xử lý ffmpeg)
build_mac.sh        build MuteNhac.app cho macOS
build_windows.bat   build MuteNhac.exe cho Windows
icon.icns           icon macOS
icon.ico            icon Windows
icon.png            icon gốc 1024px
```
