@echo off
cd /d C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A04
copilot -p "Follow the instructions in C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A04_prompt.md" --allow-all-tools --deny-tool write --add-dir C:\Users\Du200\Projects\alphasentinel\.orchestra --add-dir C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A04 < NUL > C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A04_attempt1.log 2>&1
echo EXIT %ERRORLEVEL% >> C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A04_attempt1.log
