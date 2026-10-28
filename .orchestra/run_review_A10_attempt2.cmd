@echo off
cd /d C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A10
copilot -p "Follow the instructions in C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A10_attempt2_prompt.md" --allow-all-tools --deny-tool write --add-dir C:\Users\Du200\Projects\alphasentinel\.orchestra --add-dir C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A10 < NUL > C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A10_attempt2.log 2>&1
echo EXIT %ERRORLEVEL% >> C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A10_attempt2.log

