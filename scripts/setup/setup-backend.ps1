$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..\..')
if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env'; Write-Host 'Edit .env before migration or startup' }
if (-not (Test-Path '.venv')) { py -3.12 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r backendequirements.txt
