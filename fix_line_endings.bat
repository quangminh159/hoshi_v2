@echo off
echo === DANG SUA KY TU KET THUC DONG CHO CAC FILE ===

REM Chuyen doi sang LF cho cac file shell script
echo Chuyen doi build_files.sh sang LF...
powershell -Command "(Get-Content build_files.sh -Raw).Replace(\"`r`n\", \"`n\") | Set-Content -NoNewline build_files.sh"

REM Chuyen doi wsgi_render.py sang LF
echo Chuyen doi wsgi_render.py sang LF...
powershell -Command "(Get-Content wsgi_render.py -Raw).Replace(\"`r`n\", \"`n\") | Set-Content -NoNewline wsgi_render.py"

REM Chuyen doi app.py sang LF
echo Chuyen doi app.py sang LF...
powershell -Command "(Get-Content app.py -Raw).Replace(\"`r`n\", \"`n\") | Set-Content -NoNewline app.py"

REM Them quyen thuc thi cho file shell script
echo Them quyen thuc thi cho build_files.sh...
attrib +x build_files.sh

echo === HOAN TAT ===
echo Da sua ky tu ket thuc dong va them quyen thuc thi.
echo Cac file cua ban da san sang cho viec trien khai len Render.
pause 