@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ===================================================================
echo             CÀI ĐẶT THƯ VIỆN CHO POKEMONPRO AUTO TOOL
echo ===================================================================
echo.

REM 1. Kiểm tra Python
echo [*] Đang kiểm tra Python trên hệ thống...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Không tìm thấy Python! 
    echo Vui lòng tải và cài đặt Python từ: https://www.python.org/downloads/
    echo LƯU Ý: Khi cài đặt, hãy tích chọn "Add Python to PATH" ở dưới cùng.
    echo.
    pause
    exit /b
)
for /f "tokens=*" %%i in ('python --version') do set PYTHON_VER=%%i
echo [OK] Đã tìm thấy !PYTHON_VER!
echo.

REM 2. Kiểm tra file requirements.txt
echo [*] Đang kiểm tra file requirements.txt...
set "REQ_FILE=%~dp0requirements.txt"
if not exist "%REQ_FILE%" (
    echo [ERROR] Không tìm thấy file requirements.txt tại %~dp0
    echo Vui lòng đảm bảo file requirements.txt nằm cùng thư mục với file .bat này.
    echo.
    pause
    exit /b
)
echo [OK] Đã tìm thấy file requirements.txt
echo.

REM 3. Cài đặt các thư viện Python
echo [*] Đang tiến hành nâng cấp pip và cài đặt thư viện...
echo Đang chạy: python -m pip install --upgrade pip
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [WARNING] Không thể nâng cấp pip, sẽ tiến hành cài đặt thư viện trực tiếp...
)

echo.
echo Đang chạy: python -m pip install -r "%REQ_FILE%"
python -m pip install -r "%REQ_FILE%"
if errorlevel 1 (
    echo.
    echo [ERROR] Có lỗi xảy ra trong quá trình cài đặt thư viện bằng pip.
    echo Vui lòng kiểm tra kết nối mạng hoặc thử chạy CMD với quyền Administrator.
    echo.
    pause
    exit /b
)
echo [OK] Cài đặt các thư viện Python thành công!
echo.

REM 4. Kiểm tra Tesseract OCR
echo [*] Đang kiểm tra công cụ Tesseract OCR (dùng để nhận dạng chữ)...
set "TESS_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe"

where tesseract >nul 2>&1
if errorlevel 0 (
    echo [OK] Đã tìm thấy Tesseract OCR trong biến môi trường PATH.
) else if exist "%TESS_PATH%" (
    echo [OK] Đã tìm thấy Tesseract OCR tại đường dẫn mặc định: %TESS_PATH%
) else (
    echo [WARNING] Chưa phát hiện thấy Tesseract OCR trên máy của bạn.
    echo Tool tự động của game cần Tesseract OCR để nhận diện chữ trong game.
    echo.
    echo HƯỚNG DẪN CÀI ĐẶT TESSERACT OCR:
    echo 1. Tải bộ cài cho Windows tại: https://github.com/UB-Mannheim/tesseract/wiki
    echo 2. Chạy bộ cài và cài đặt vào đường dẫn mặc định: C:\Program Files\Tesseract-OCR
    echo 3. Chạy lại file cài đặt này hoặc file 'run_gui.bat' sau khi cài xong.
    echo.
)

echo ===================================================================
echo             CÀI ĐẶT THÀNH CÔNG VÀ HOÀN TẤT!
echo  Bạn có thể chạy tool bằng cách nhấp đúp vào:
echo  - run_gui.bat (để chạy giao diện đồ họa)
echo  - run_pokemon_tool.bat (để chạy giao diện dòng lệnh CMD)
echo ===================================================================
echo.
pause
