@echo off
chcp 65001 >nul
title Agente CLI - Vision

:: Cores e formatação
echo.
echo ============================================
echo           AGENTE CLI - VISION
echo ============================================
echo.

:: Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python não encontrado!
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
    echo [INFO] Ativando ambiente virtual para instalação...
    call .\.venv\Scripts\activate.bat
) else (
    echo [OK] Ambiente virtual já existe.
    echo [INFO] Ativando ambiente virtual...
    call .\.venv\Scripts\activate.bat
)

:: Verificar se requirements.txt existe
if not exist "requirements.txt" (
    echo [AVISO] requirements.txt não encontrado!
    echo Pulando instalação de dependências...
) else (
    echo [INFO] Verificando/installando dependências...
    pip install -r requirements.txt -q
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar dependências!
        pause
        exit /b 1
    )
    echo [OK] Dependências verificadas!
)

echo.
echo ============================================
echo            INICIANDO AGENTE...
echo ============================================
echo.

:: Iniciar o projeto
python main.py

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
