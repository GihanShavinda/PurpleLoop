$ErrorActionPreference='Stop'
Set-Location (Join-Path $PSScriptRoot '..\..rontend')
if (-not (Test-Path 'node_modules')) { npm install }
npm start
