@echo off
chcp 65001 >nul
title Kids Animation Studio AI
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
echo Abrindo o painel em http://localhost:8765  (feche esta janela para encerrar)
python kas.py painel
pause
