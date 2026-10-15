@echo off
rem ======================================================================
rem  gerar_exe.bat - instala e compila a Central de Suporte
rem
rem  O que este arquivo faz:
rem    1) cria a pasta "Central de Suporte" NA AREA DE TRABALHO
rem    2) compila o CentralSuporte.exe dentro dela (arquivos de compilacao
rem       ficam na subpasta "compilacao")
rem    3) MOVE o central_suporte.py e este gerar_exe.bat para a pasta nova,
rem       sem deixar copias no lugar de origem
rem
rem  A pasta e portatil: depois de pronta, pode ser arrastada para qualquer
rem  lugar (outra pasta, outro disco, pendrive). O .exe continua funcionando.
rem
rem  Coloque este arquivo na MESMA pasta do central_suporte.py e execute.
rem  Para recompilar depois, execute o gerar_exe.bat de DENTRO da pasta
rem  "Central de Suporte": ele detecta isso e recompila no proprio lugar.
rem ======================================================================

rem UTF-8 no terminal (acentos corretos) e titulo da janela
chcp 65001 >nul
title Instalar Central de Suporte

rem Garante que o script rode na pasta onde ele esta salvo (origem dos arquivos)
cd /d "%~dp0"

rem Nome da pasta que sera criada na Area de Trabalho
set "FOLDER_NAME=Central de Suporte"

rem ----------------------------------------------------------------------
rem  Define onde o programa fica (INSTALL_DIR)
rem ----------------------------------------------------------------------
set "INSTALL_DIR="

rem Caso 1 - recompilacao: se ja existe a subpasta "compilacao" ao lado deste
rem .bat, ele esta dentro de uma instalacao pronta. Recompila no proprio lugar
rem (assim nao recria a pasta na Area de Trabalho se ela foi movida).
if exist "%~dp0compilacao\" for %%I in ("%~dp0.") do set "INSTALL_DIR=%%~fI"

rem Caso 2 - primeira instalacao: descobre a Area de Trabalho REAL do usuario
rem (funciona mesmo com ela sincronizada no OneDrive) e usa nela a nova pasta.
if not defined INSTALL_DIR for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do set "DESKTOP=%%D"
if not defined INSTALL_DIR if not defined DESKTOP set "DESKTOP=%USERPROFILE%\Desktop"
if not defined INSTALL_DIR set "INSTALL_DIR=%DESKTOP%\%FOLDER_NAME%"

echo ======================================================
echo  Instalando a Central de Suporte
echo  Destino: %INSTALL_DIR%
echo ======================================================
echo.

rem --- Verificacao 1: o codigo-fonte precisa estar na mesma pasta deste .bat ---
if not exist "%~dp0central_suporte.py" (
  echo ERRO: coloque este arquivo na mesma pasta do central_suporte.py
  pause
  exit /b 1
)

rem --- Verificacao 2: o Python precisa estar instalado e no PATH ---
where python >nul 2>&1
if errorlevel 1 (
  echo ERRO: Python nao encontrado. Instale em https://www.python.org/downloads/
  echo Marque a opcao "Add python.exe to PATH" durante a instalacao.
  pause
  exit /b 1
)

rem --- Passo 1: criar a pasta de destino e a subpasta de compilacao ---
echo [1/4] Criando a pasta da Central de Suporte...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%INSTALL_DIR%\compilacao" mkdir "%INSTALL_DIR%\compilacao"
if not exist "%INSTALL_DIR%\compilacao" (
  echo ERRO: nao foi possivel criar "%INSTALL_DIR%"
  pause
  exit /b 1
)

rem --- Passo 2: instalar/atualizar o PyInstaller (empacotador) ---
echo [2/4] Instalando/atualizando o PyInstaller...
python -m pip install --upgrade pyinstaller
if errorlevel 1 (
  echo ERRO ao instalar o PyInstaller.
  pause
  exit /b 1
)

rem --- Passo 3: compilar ---
rem O codigo e lido de onde esta agora (%~dp0). So depois que a compilacao der
rem certo os arquivos sao movidos: se algo falhar, nada some do lugar de origem
rem e voce pode tentar de novo.
rem   --onefile    : gera um unico .exe (portatil)
rem   --noconsole  : nao abre janela preta atras da interface
rem   --uac-admin  : o .exe ja pede permissao de administrador ao abrir
rem   --clean      : limpa o cache de compilacoes anteriores
rem   --name       : nome do executavel final
rem   --distpath   : o .exe final e gravado direto na pasta do programa
rem   --workpath   : arquivos temporarios da compilacao (pasta "compilacao")
rem   --specpath   : o arquivo .spec tambem fica na pasta "compilacao"
echo.
echo [3/4] Compilando (pode levar cerca de um minuto)...
python -m PyInstaller --onefile --noconsole --uac-admin --clean --name CentralSuporte ^
  --distpath "%INSTALL_DIR%" ^
  --workpath "%INSTALL_DIR%\compilacao\build" ^
  --specpath "%INSTALL_DIR%\compilacao" ^
  "%~dp0central_suporte.py"
if errorlevel 1 (
  echo ERRO na compilacao.
  pause
  exit /b 1
)

rem --- Passo 4: MOVER o codigo-fonte para a pasta nova ---
rem "move" tira o arquivo do lugar de origem (nao deixa copia na Area de Trabalho).
rem Se este .bat ja esta dentro da pasta de destino, nao ha nada para mover.
echo [4/4] Organizando arquivos...
if /I not "%~dp0"=="%INSTALL_DIR%\" move /y "%~dp0central_suporte.py" "%INSTALL_DIR%\central_suporte.py" >nul

echo.
echo ======================================================
echo  Pronto!
echo  Pasta    : %INSTALL_DIR%
echo  Programa : CentralSuporte.exe
echo  Voce pode mover a pasta para onde quiser.
echo ======================================================
rem Abre a pasta pronta no Explorer
start "" explorer.exe "%INSTALL_DIR%"
pause

rem --- Mover este proprio .bat (deve ser a ULTIMA coisa do arquivo) ---
rem O cmd le o .bat aos poucos; mover o arquivo no meio da execucao o quebraria.
rem O truque "(goto) 2>nul" encerra a leitura do .bat antes do move rodar,
rem o que libera o arquivo para ser movido.
if /I "%~dp0"=="%INSTALL_DIR%\" exit /b 0
(goto) 2>nul & move /y "%~f0" "%INSTALL_DIR%\gerar_exe.bat" >nul
