@echo off
chcp 65001 >nul
cd /d "%~dp0"
title AeroSuite - corrida autonoma (no cerrar)
powercfg /change standby-timeout-ac 0
set "PATH=%USERPROFILE%\.local\bin;%APPDATA%\npm;%ProgramFiles%\GitHub CLI;%ProgramFiles%\Git\cmd;%PATH%"
where claude >nul 2>&1 || (echo No se encuentra Claude Code. Revisa el paso 3 de la guia. & pause & exit /b 1)
where gh >nul 2>&1 || (echo No se encuentra GitHub CLI. Revisa el paso 2 de la guia. & pause & exit /b 1)
gh auth status >nul 2>&1 || (echo GitHub CLI no tiene sesion iniciada. Revisa el paso 5 de la guia. & pause & exit /b 1)
powercfg /change hibernate-timeout-ac 0
if not exist .venv (
  py -3.11 -m venv .venv
  .venv\Scripts\python -m pip install -r requirements-core.txt
  .venv\Scripts\python -m pip install --no-deps ./vendor/ADRpy
)
set MAX=12
set PLAN=AUTONOMOUS_RUN_F6.md
if exist FASE_COMPLETA.flag del FASE_COMPLETA.flag
for /L %%i in (1,1,%MAX%) do (
  if exist FASE_COMPLETA.flag goto fin
  echo Corrida %%i en curso. Claude Code trabaja en segundo plano; el detalle queda en autonomo.log
  echo ==== Corrida %%i  %date% %time% ==== >> autonomo.log
  claude -p "Lee CLAUDE.md y %PLAN% y ejecuta la corrida autonoma desde donde indique la bitacora. Usa .venv\Scripts\python para Python. No hagas preguntas." --permission-mode bypassPermissions --max-turns 300 --disallowedTools "Edit(vendor/**)" "Bash(git push --force:*)" "Bash(git push -f:*)" "Bash(git push origin main:*)" "Bash(git reset --hard:*)" "Bash(rm -rf:*)" "Bash(gh pr merge:*)" "Bash(gh repo delete:*)" >> autonomo.log 2>&1
  if exist FASE_COMPLETA.flag goto fin
  echo Esperando 30 min antes de reintentar... >> autonomo.log
  timeout /t 1800 /nobreak >nul
)
:fin
echo ==== Fin %date% %time% ==== >> autonomo.log
