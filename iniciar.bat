@echo off
chcp 65001 >nul
title Agente CLI - Vision

:: Salva o diretorio onde o usuario estava antes de qualquer cd
set "LAUNCH_DIR=%CD%"

:: Muda para a pasta do agente (necessario para .venv e requirements.txt)
cd /d "%~dp0"

:: Cores e formatacao
echo.
echo ============================================
echo           AGENTE CLI - VISION
echo ============================================
echo.

:: Verificar se Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo Instale o Python 3.8+ e tente novamente.
    pause
    exit /b 1
)

:: Verificar se o ambiente virtual existe
if not exist ".venv" (
    echo [INFO] Criando ambiente virtual...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar ambiente virtual!
        pause
        exit /b 1
    )
    echo [OK] Ambiente virtual criado com sucesso!
    echo.
    echo [INFO] Ativando ambiente virtual para instalacao...
    call .\.venv\Scripts\activate.bat
) else (
    echo [OK] Ambiente virtual ja existe.
    echo [INFO] Ativando ambiente virtual...
    call .\.venv\Scripts\activate.bat
)

:: Verificar se requirements.txt existe
if not exist "requirements.txt" (
    echo [AVISO] requirements.txt nao encontrado!
    echo Pulando instalacao de dependencias...
) else (
    echo [INFO] Verificando/instalando dependencias...
    pip install -r requirements.txt -q
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar dependencias!
        pause
        exit /b 1
    )
    echo [OK] Dependencias verificadas!
)

echo.
echo ============================================
echo            INICIANDO AGENTE...
echo ============================================
echo [INFO] Diretorio de trabalho: %LAUNCH_DIR%
echo.

:: Inicia o agente com o diretorio original do usuario
python main.py --cwd "%LAUNCH_DIR%"

:: Se o script terminar, manter a janela aberta
if errorlevel 1 (
    echo.
    echo [ERRO] O agente foi fechado com erro.
    pause
) else (
    echo.
    echo [OK] Agente finalizado.
    pause
)
