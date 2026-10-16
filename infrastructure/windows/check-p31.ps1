param([string]$ProxyHost='192.168.37.1', [int]$ProxyPort=8443)
$ErrorActionPreference='Stop'
Write-Host 'Local FastAPI:'
Invoke-RestMethod 'http://127.0.0.1:8000/health' | ConvertTo-Json
Write-Host 'TLS endpoint port:'
Test-NetConnection -ComputerName $ProxyHost -Port $ProxyPort
Write-Host 'Ensure the collector trusts your lab CA; do not disable certificate validation.'
