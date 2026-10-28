$env:TEMP='C:\Users\Du200\Projects\alphasentinel\.orchestra\tmp'; $env:TMP=$env:TEMP
Set-Location 'C:\Users\Du200\Projects\alphasentinel\.orchestra\review_final'
$prompt=[IO.File]::ReadAllText('C:\Users\Du200\Projects\alphasentinel\.orchestra\final_review_gemini_prompt.md')
& 'C:\Users\Du200\AppData\Local\agy\bin\agy.exe' --model gemini-3.8-flash-high --dangerously-skip-permissions -p $prompt *> 'C:\Users\Du200\Projects\alphasentinel\.orchestra\final_review_gemini.log'
"EXIT $LASTEXITCODE" | Add-Content 'C:\Users\Du200\Projects\alphasentinel\.orchestra\final_review_gemini.log'