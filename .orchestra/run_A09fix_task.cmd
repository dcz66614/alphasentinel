@echo off
cd /d C:\Users\Du200\Projects\alphasentinel-codex
C:\Users\Du200\.grok\bin\grok.exe -m grok-4.7 --reasoning-effort high --always-approve --prompt-file C:\Users\Du200\Projects\alphasentinel\.orchestra\A09fix_grok_prompt.md < NUL > C:\Users\Du200\Projects\alphasentinel\.orchestra\A09fix_grok.log 2>&1
echo EXIT %ERRORLEVEL% >> C:\Users\Du200\Projects\alphasentinel\.orchestra\A09fix_grok.log




