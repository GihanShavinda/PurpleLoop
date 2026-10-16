param([string]$ProjectRoot = (Resolve-Path "$PSScriptRoot\.." ).Path)
$ErrorActionPreference = 'Stop'
Set-Location $ProjectRoot
$python = Join-Path $ProjectRoot 'backend\.venv\Scripts\python.exe'
if (!(Test-Path $python)) {throw 'Backend virtual environment missing'}
Write-Host '[1/5] Import all application modules'
& $python -c 'import backend.models; import backend.main; print("Import OK")'
if ($LASTEXITCODE -ne 0){throw 'Import failed'}
Write-Host '[2/5] Verify Alembic head without modifying schema'
& $python -m alembic -c .\backend\alembic.ini current
if ($LASTEXITCODE -ne 0){throw 'Alembic failed'}
Write-Host '[3/5] P19 tests'
& $python -m pytest tests\test_p19_assurance.py tests\test_p19_integration_static.py -v
if ($LASTEXITCODE -ne 0){throw 'P19 tests failed'}
Write-Host '[4/5] Full backend test suite'
& $python -m pytest tests -q
if ($LASTEXITCODE -ne 0){throw 'Regression failed'}
Write-Host '[5/5] Angular production build'
Push-Location frontend
try {npm run build; if ($LASTEXITCODE -ne 0){throw 'Angular build failed'}} finally {Pop-Location}
Write-Host 'P19 checks complete. Manual auth and TLS checks still required.'
