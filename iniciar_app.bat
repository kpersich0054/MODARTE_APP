@echo off
cd /d "%~dp0"

echo =====================================
echo   MODARTE - Inicializando Aplicacao
echo =====================================

REM Verificar se o venv existe
if not exist "venv\Scripts\python.exe" (
    echo ERRO: Ambiente virtual nao encontrado.
    echo Execute: python -m venv venv
    pause
    exit /b
)

REM Instalar dependencias (se necessario)
venv\Scripts\python.exe -m pip install -r requirements.txt --quiet

REM Iniciar a aplicacao
venv\Scripts\python.exe -m streamlit run app.py

exit
