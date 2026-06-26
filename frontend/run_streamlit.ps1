$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)

$python = "python"
if (Test-Path ".\venv\Scripts\python.exe") {
    $venvHasStreamlit = & ".\venv\Scripts\python.exe" -c "import importlib.util; print(bool(importlib.util.find_spec('streamlit')))"
    if ($venvHasStreamlit.Trim() -eq "True") {
        $python = ".\venv\Scripts\python.exe"
    }
}

& $python -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
