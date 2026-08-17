@echo off
REM Build app desktop cho Windows bang PyInstaller
REM Yeu cau: Python 3.10+ (https://python.org), ffmpeg.exe (https://www.gyan.dev/ffmpeg/builds/)
REM Cach chay: double-click hoac mo CMD trong thu muc roi go: build_windows.bat

setlocal
cd /d "%~dp0"

echo ==^> Tao virtual env
python -m venv .venv
if errorlevel 1 goto :error

call .venv\Scripts\activate.bat

echo ==^> Cai PyInstaller
python -m pip install --upgrade pip
python -m pip install pyinstaller
if errorlevel 1 goto :error

REM Tu dong nhung ffmpeg.exe neu nam canh script
set EXTRA=
if exist "%~dp0ffmpeg.exe" (
    echo ==^> Phat hien ffmpeg.exe — se nhung vao bundle
    set EXTRA=--add-binary "%~dp0ffmpeg.exe;."
)

echo ==^> Build .exe
pyinstaller --noconfirm --windowed --onefile ^
    --name "MuteNhac" ^
    %EXTRA% ^
    mute_app.py
if errorlevel 1 goto :error

echo.
echo ==^> Xong! App o: dist\MuteNhac.exe
goto :eof

:error
echo.
echo *** Co loi xay ra. Kiem tra log o tren. ***
exit /b 1
