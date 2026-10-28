@echo off
setlocal
cd /d "%~dp0"
py -m pip install --upgrade pyinstaller psutil
if errorlevel 1 exit /b 1
py -m PyInstaller --noconfirm --clean --onefile --windowed --uac-admin --name "FinalsPing" --icon "FinalsPing.ico" --add-data "FinalsPing.ico;." --collect-all psutil --hidden-import engine FinalsPing.pyw
if errorlevel 1 exit /b 1
echo Built: dist\FinalsPing.exe
