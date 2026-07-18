$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$target = (Get-Location).Path
Remove-Item -LiteralPath (Join-Path $target "RELEASE_NOTES_PENDING(1).md") -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $target "RELEASE_NOTES_PENDING_ERGAENZUNG.md") -Force -ErrorAction SilentlyContinue
Write-Host "Alte falsche Release-Notizdateien entfernt."
Write-Host "Dateien dieses Pakets bitte direkt im MediaHub-Plugins-Projektordner entpacken."
