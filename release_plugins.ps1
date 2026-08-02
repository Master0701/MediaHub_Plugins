[CmdletBinding()]
param(
    [string]$Tag,
    [switch]$SkipTests,
    [switch]$NoPush,
    [switch]$Yes
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python wurde nicht gefunden."
}

$argsList = @("$root\release_plugins.py")
if ($Tag) { $argsList += @("--tag", $Tag) }
if ($SkipTests) { $argsList += "--skip-tests" }
if ($NoPush) { $argsList += "--no-push" }
if ($Yes) { $argsList += "--yes" }

& $python.Source @argsList
if ($LASTEXITCODE -ne 0) {
    throw "Release-Assistent wurde mit Fehlercode $LASTEXITCODE beendet."
}
