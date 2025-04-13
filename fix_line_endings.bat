@echo off
echo === ĐANG SỬA KÝ TỰ KẾT THÚC DÒNG CHO CÁC FILE SHELL SCRIPT ===

REM Chuyển đổi sang LF cho các file shell script
echo Chuyển đổi build_files.sh sang LF...
powershell -Command "(Get-Content build_files.sh -Raw).Replace(\"`r`n\", \"`n\") | Set-Content -NoNewline build_files.sh"

REM Thêm quyền thực thi cho file shell script
echo Thêm quyền thực thi cho build_files.sh...
attrib +x build_files.sh

echo === HOÀN TẤT ===
echo Đã sửa ký tự kết thúc dòng và thêm quyền thực thi.
echo Các file của bạn đã sẵn sàng cho việc triển khai lên Render.
pause 