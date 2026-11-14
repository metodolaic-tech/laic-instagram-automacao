@echo off
chcp 65001 >nul
title Kids Animation Studio AI - Instalacao
echo ============================================================
echo   Kids Animation Studio AI - instalacao no Windows
echo   Tudo gratuito. Nada pago sera instalado ou ativado.
echo ============================================================
echo.
where winget >nul 2>nul
if errorlevel 1 (
  echo [!] O winget nao foi encontrado. Instale manualmente:
  echo     Python 3.13  https://www.python.org/downloads/
  echo     Blender 4.2+ https://www.blender.org/download/
  echo     FFmpeg       https://www.gyan.dev/ffmpeg/builds/
  echo     e rode este arquivo de novo.
  pause
  exit /b 1
)
where python >nul 2>nul || winget install -e --id Python.Python.3.13 --accept-source-agreements --accept-package-agreements
where ffmpeg >nul 2>nul || winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
if not exist "C:\Program Files\Blender Foundation" winget install -e --id BlenderFoundation.Blender --accept-source-agreements --accept-package-agreements
echo.
echo Criando ambiente Python do estudio (.venv)...
python -m venv .venv || py -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo Baixando vozes gratuitas em portugues (Piper)...
python kas.py baixar-vozes
echo.
python kas.py diagnostico
echo.
echo Se o FFmpeg ou o Blender aparecerem como FALTANDO, feche esta janela,
echo abra uma nova (para atualizar o PATH) e rode iniciar_painel.bat.
pause
