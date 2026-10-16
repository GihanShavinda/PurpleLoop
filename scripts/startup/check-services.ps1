$ErrorActionPreference='Continue'
Write-Host 'PostgreSQL Services:'
Get-Service '*postgres*' | Format-Table Name,Status
Write-Host 'Windows Redis Services/Processes (if installed on host):'
Get-Service '*redis*' | Format-Table Name,Status
Get-Process '*redis*' | Select-Object ProcessName,Id
foreach($item in @(@('PostgreSQL','127.0.0.1',5432),@('Redis','127.0.0.1',6379),@('Neo4j Bolt','127.0.0.1',7687),@('Neo4j Browser','127.0.0.1',7474))) {
 $result=Test-NetConnection -ComputerName $item[1] -Port $item[2] -WarningAction SilentlyContinue
 Write-Host "$($item[0]) $($item[1]):$($item[2]): $($result.TcpTestSucceeded)"
}
try { Invoke-RestMethod http://127.0.0.1:8000/health | ConvertTo-Json } catch { Write-Warning 'API is not running yet.' }
