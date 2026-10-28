$env:TEMP='C:\Users\Du200\Projects\alphasentinel\.orchestra\tmp'; $env:TMP=$env:TEMP
$env:OPENCODE_PERMISSION='{"edit":"deny"}'
Set-Location 'C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A11'
$p=[IO.File]::ReadAllText('C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A11_r2_prompt.md')
opencode run -m opencode/deepseek-v4.1-flash-free --title review_A11_r2 $p --file 'C:\Users\Du200\Projects\alphasentinel\.orchestra\A11_grok_prompt.md' --file 'C:\Users\Du200\Projects\alphasentinel\.orchestra\A11_report.md' --file 'C:\Users\Du200\Projects\alphasentinel\.orchestra\FINAL_REVIEW_gemini.md' *> 'C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A11_r2_opencode.log'
"EXIT $LASTEXITCODE" | Add-Content 'C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A11_r2_opencode.log'