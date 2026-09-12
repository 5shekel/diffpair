param([string]$Label = 'unclassified')
$ErrorActionPreference = 'Stop'
$captureExe = Join-Path $PSScriptRoot 'build/usb3_capture.exe'
if (-not (Test-Path -LiteralPath $captureExe)) {
    throw 'Build usb3_capture.cpp as described in README.md before running this capture.'
}
$captureText = & $captureExe
$captureExit = $LASTEXITCODE
if ($captureExit -notin @(0,2)) { throw "USB inventory failed: exit $captureExit" }
$capture = $captureText | ConvertFrom-Json
$timestamp = [DateTime]::UtcNow
$capture | Add-Member -NotePropertyName captured_at_utc -NotePropertyValue $timestamp.ToString('o')
$capture | Add-Member -NotePropertyName operator_label -NotePropertyValue $Label
$capture | Add-Member -NotePropertyName executable_sha256 -NotePropertyValue (Get-FileHash -LiteralPath $captureExe -Algorithm SHA256).Hash
$capture | Add-Member -NotePropertyName source_sha256 -NotePropertyValue (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'usb3_capture.cpp') -Algorithm SHA256).Hash
$captureFolder = Join-Path $PSScriptRoot 'captures'
New-Item -ItemType Directory -Force -Path $captureFolder | Out-Null
$capturePath = Join-Path $captureFolder ($timestamp.ToString('yyyyMMddTHHmmssfffZ')+'.json')
$capture | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $capturePath -Encoding utf8
Write-Output $capturePath
Write-Output "USB3 connections: $(@($capture.usb3_connections).Count); query errors: $(@($capture.errors).Count)"
if ($captureExit -eq 2) { Write-Warning 'Capture is incomplete; inspect its errors before drawing conclusions.' }
