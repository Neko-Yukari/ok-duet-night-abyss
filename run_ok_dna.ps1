#!/usr/bin/env pwsh
#Requires -Version 5.1
<#
.SYNOPSIS
    Launch ok-dna from any folder (portable).
.DESCRIPTION
    This script locates itself, finds the project root, activates the bundled
    .venv, and runs main.py with pythonw.exe so no console window appears.
    If pythonw.exe is missing, it falls back to python.exe.
#>

$ErrorActionPreference = "Stop"

# Get the directory where this script lives, resolving any symlinks.
$scriptPath = $MyInvocation.MyCommand.Path
if (-not $scriptPath) {
    $scriptPath = $PSCommandPath
}
$projectRoot = Split-Path -Parent (Resolve-Path $scriptPath).Path

$pythonDir = Join-Path $projectRoot ".venv\Scripts"
$pythonw = Join-Path $pythonDir "pythonw.exe"
$python = Join-Path $pythonDir "python.exe"
$mainPy = Join-Path $projectRoot "main.py"

if (-not (Test-Path -LiteralPath $mainPy -PathType Leaf)) {
    Write-Error "main.py not found at: $mainPy"
    exit 1
}

if (Test-Path -LiteralPath $pythonw -PathType Leaf) {
    $exe = $pythonw
} elseif (Test-Path -LiteralPath $python -PathType Leaf) {
    $exe = $python
} else {
    # Try a system-wide fallback if the venv is missing (portable copy without venv).
    $sysPython = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
    if (-not $sysPython) {
        $sysPython = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    }
    if ($sysPython) {
        $exe = $sysPython
    } else {
        Write-Error "No Python interpreter found. Please run: uv sync"
        exit 1
    }
}

# pythonw.exe does not block and has no console; we start it detached.
Start-Process -FilePath $exe -ArgumentList @($mainPy) -WorkingDirectory $projectRoot -WindowStyle Hidden
