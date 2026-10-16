$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $root
$python=Join-Path $root 'backend\.venv\Scripts\python.exe'
if (!(Test-Path $python)) { throw 'Backend Python venv not found at backend\.venv' }
& $python -m alembic -c .\backend\alembic.ini upgrade head
if ($LASTEXITCODE -ne 0) { throw 'P3 migration failed' }
& $python -m alembic -c .\backend\alembic.ini current
