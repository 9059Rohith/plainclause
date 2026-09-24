$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    throw 'Create .venv and install backend/requirements.lock.txt first.'
}

$env:PYTHONPATH = 'backend'
& $python -m pytest backend/tests -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

foreach ($script in @('typecheck', 'lint', 'build', 'test:e2e')) {
    & npm run $script
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& npm audit --audit-level=high
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $python -m pip check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
