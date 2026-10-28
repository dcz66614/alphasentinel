$env:TEMP='C:\Users\Du200\Projects\alphasentinel\.orchestra\tmp'; $env:TMP=$env:TEMP
Set-Location 'C:\Users\Du200\Projects\alphasentinel-codex'
$p = Get-Content 'C:\Users\Du200\Projects\alphasentinel\.orchestra\A01_opencode_prompt.md' -Raw -Encoding utf8
opencode run -m opencode/deepseek-v4.1-flash-free --title A01 $p *> 'C:\Users\Du200\Projects\alphasentinel\.orchestra\A01_opencode.log'
"EXIT $LASTEXITCODE" | Add-Content 'C:\Users\Du200\Projects\alphasentinel\.orchestra\A01_opencode.log'

