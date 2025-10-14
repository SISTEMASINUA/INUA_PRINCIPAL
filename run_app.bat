@echo off
setlocal
REM Ejecuta la app con Python 3.11 (lector real) si existe, si no, usa .venv normal
set ROOT=%~dp0
set APPDIR=%ROOT%
set PY311=%ROOT%\.venv311\Scripts\python.exe
set PYVENV=%ROOT%\.venv\Scripts\python.exe

if exist "%PY311%" (
  set PY=%PY311%
) else if exist "%PYVENV%" (
  set PY=%PYVENV%
) else (
  echo No se encontró el intérprete Python en .venv311 ni .venv
  exit /b 1
)

pushd "%APPDIR%"
"%PY%" main.py
popd
