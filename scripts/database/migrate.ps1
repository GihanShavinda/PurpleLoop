$ErrorActionPreference='Stop'
Set-Location (Join-Path $PSScriptRoot '..\..')
& .\.venv\Scripts\python.exe -m alembic -c backendlembic.ini upgrade head
