@echo off
rem Drag and drop image folder(s) onto this file to combine all images into ONE PDF.
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
if "%~1"=="" (
    echo Drag and drop image folders onto this file.
    pause
    exit /b
)
python "%~dp0images_to_single_pdf.py" %*
pause
