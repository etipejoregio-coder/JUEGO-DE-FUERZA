@echo off
setlocal
cd /d "%~dp0"

echo === Instalando dependencias ===
python -m pip install -r requirements.txt
if errorlevel 1 goto error

echo === Generando ejecutable ===
python -m PyInstaller --noconfirm --onefile --windowed --name BatallaDeFuerza --add-data "assets;assets" main.py
if errorlevel 1 goto error

echo.
echo Listo. El ejecutable esta en: dist\BatallaDeFuerza.exe
pause
exit /b 0

:error
echo.
echo Ocurrio un error. Revisa que Python 3.10+ este instalado y en el PATH.
pause
exit /b 1
