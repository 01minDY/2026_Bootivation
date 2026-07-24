$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$pythonPath = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw ".venv\Scripts\python.exe 파일이 없습니다."
}

& $pythonPath -m uvicorn main:app --host 0.0.0.0 --port 8000
