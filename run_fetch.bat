@echo off
setlocal
for /f "delims=" %%i in (.env) do set %%i
python smart_login_and_fetch.py
pause
