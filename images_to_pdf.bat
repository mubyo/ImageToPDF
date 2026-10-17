@echo off
rem Drag and drop image folder(s) onto this file to create PDF(s).
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
if "%~1"=="" (
    echo Drag and drop an image folder onto this file.
    pause
    exit /b
)
python "%~dp0images_to_pdf.py" %*
pause
