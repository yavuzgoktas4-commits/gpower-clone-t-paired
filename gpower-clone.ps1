#!/usr/bin/env pwsh
$env:PYTHONPATH = "$PSScriptRoot;$env:PYTHONPATH"
python -m src.cli.main @args
exit $LASTEXITCODE
