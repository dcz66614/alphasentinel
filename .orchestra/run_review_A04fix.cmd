@echo off
cd /d C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A04fix
copilot -p "Follow the instructions in C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A04fix_prompt.md" --allow-all-tools --deny-tool write --add-dir C:\Users\Du200\Projects\alphasentinel\.orchestra --add-dir C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A04fix < NUL > C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A04fix_attempt1.log 2>&1
echo EXIT %ERRORLEVEL% >> C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A04fix_attempt1.log
