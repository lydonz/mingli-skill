@echo off
setlocal

set "SKILL_NAME=mingli-skill"
set "TARGET_DIR=%~1"
if "%TARGET_DIR%"=="" set "TARGET_DIR=%USERPROFILE%\.codex\skills"
set "DESTINATION=%TARGET_DIR%\%SKILL_NAME%"

if exist "%DESTINATION%" (
  echo Installation target already exists: %DESTINATION%
  echo Choose another target directory or remove the existing skill first.
  exit /b 1
)

mkdir "%DESTINATION%" || exit /b 1
robocopy "%~dp0" "%DESTINATION%" /E /XD ".git" "node_modules" "cache" "__pycache__" ".pytest_cache" >nul
if %ERRORLEVEL% GEQ 8 (
  echo Installation copy failed.
  exit /b 1
)

if not exist "%DESTINATION%\SKILL.md" (
  echo Installation failed: SKILL.md is missing.
  exit /b 1
)

echo Installed %SKILL_NAME% to %DESTINATION%
