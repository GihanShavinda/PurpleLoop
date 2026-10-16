param([string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path)
$ErrorActionPreference = 'Stop'
Set-Location $ProjectRoot
$python = Join-Path $ProjectRoot 'backend\.venv\Scripts\python.exe'
if (!(Test-Path $python)) {throw 'Backend virtual environment not found'}
function Run-Checked([string]$label,[string]$file,[string[]]$arguments) {
 Write-Host "== $label ==" -ForegroundColor Cyan
 & $file @arguments
 if ($LASTEXITCODE -ne 0) {throw "$label failed with exit code $LASTEXITCODE"}
}
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$directory = Join-Path $ProjectRoot "p20-local-evidence\$stamp"
New-Item -ItemType Directory -Force -Path $directory | Out-Null
try {
 Run-Checked 'Model and route import' $python @('-c','import backend.main; print("P20 imports OK")')
 Run-Checked 'Alembic revision' $python @('-m','alembic','-c','.\backend\alembic.ini','current')
 Run-Checked 'P20 unit tests' $python @('-m','pytest','tests\test_p20_evaluation.py','-v','--junitxml', (Join-Path $directory 'p20-unit.xml'))
 Run-Checked 'Full regression suite' $python @('-m','pytest','tests','-v','--junitxml',(Join-Path $directory 'regression.xml'))
 Push-Location (Join-Path $ProjectRoot 'frontend')
 try {Run-Checked 'Angular production build' 'npm.cmd' @('run','build')} finally {Pop-Location}
 "Verified locally at $(Get-Date -Format o). Review the logs and perform manual validation." | Set-Content (Join-Path $directory 'verification-summary.txt')
 Write-Host "Saved test evidence in $directory" -ForegroundColor Green
} catch {
 Write-Error $_
 exit 1
}
