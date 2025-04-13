@echo off
echo === DANG SUA KY TU KET THUC DONG CHO CAC FILE ===

echo Dang tim cac file Python trong thu muc hoshi...
for /R "hoshi" %%F in (*.py) do (
    echo Kiem tra file %%F...
    powershell -Command "if ((Get-Item '%%F').Length -gt 0) { (Get-Content '%%F' -Raw).Replace(\"`r`n\", \"`n\") | Set-Content -NoNewline '%%F'; Write-Host 'Da chuyen doi %%F sang LF' } else { Write-Host 'File %%F trong, bo qua' }"
)

REM Chuyen doi cac file Python chinh
echo Chuyen doi wsgi_render.py sang LF...
powershell -Command "if ((Get-Item 'wsgi_render.py').Length -gt 0) { (Get-Content 'wsgi_render.py' -Raw).Replace(\"`r`n\", \"`n\") | Set-Content -NoNewline 'wsgi_render.py' }"

echo Chuyen doi app.py sang LF...
powershell -Command "if ((Get-Item 'app.py').Length -gt 0) { (Get-Content 'app.py' -Raw).Replace(\"`r`n\", \"`n\") | Set-Content -NoNewline 'app.py' }"

echo Chuyen doi wsgi.py sang LF...
powershell -Command "if ((Get-Item 'wsgi.py').Length -gt 0) { (Get-Content 'wsgi.py' -Raw).Replace(\"`r`n\", \"`n\") | Set-Content -NoNewline 'wsgi.py' }"

REM Chuyen doi build_files.sh va them quyen thuc thi
echo Chuyen doi build_files.sh sang LF...
powershell -Command "if ((Get-Item 'build_files.sh').Length -gt 0) { (Get-Content 'build_files.sh' -Raw).Replace(\"`r`n\", \"`n\") | Set-Content -NoNewline 'build_files.sh' }"

echo Them quyen thuc thi cho build_files.sh...
attrib +x build_files.sh

echo === HOAN TAT ===
echo Da sua ky tu ket thuc dong va them quyen thuc thi.
echo Cac file cua ban da san sang cho viec trien khai len Render.
pause 