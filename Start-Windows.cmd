@echo off
setlocal
chcp 65001 >nul
title Marketing Court
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launch-windows.ps1"
if errorlevel 1 (
  echo.
  echo 启动未完成。请保留上面的提示并联系项目维护者。
  pause
)
