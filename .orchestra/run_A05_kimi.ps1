$env:WB_RELAY_KEY=(Get-Content 'C:\Users\Du200\Downloads\workbuddy反代key.txt')[0].Trim()
$env:OPENCODE_CONFIG='C:\Users\Du200\Projects\alphasentinel\.orchestra\opencode_wb.json'
$env:TEMP='C:\Users\Du200\Projects\alphasentinel\.orchestra\tmp'; $env:TMP=$env:TEMP
Set-Location 'C:\Users\Du200\Projects\alphasentinel-wb'
$p=[IO.File]::ReadAllText('C:\Users\Du200\Projects\alphasentinel\.orchestra\A05_kimi_prompt.md')
opencode run -m wb/kimi-k3.1-pro --title A05 $p *> 'C:\Users\Du200\Projects\alphasentinel\.orchestra\A05_kimi.log'
"EXIT $LASTEXITCODE" | Add-Content 'C:\Users\Du200\Projects\alphasentinel\.orchestra\A05_kimi.log'