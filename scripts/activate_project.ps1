# Project environment loader for CIMET Voice POC

$ProjectRoot = Split-Path -Parent $PSScriptRoot

# Keep project caches and temporary files on D:
$ProjectCache = Join-Path $ProjectRoot ".cache"
$ProjectTemp = Join-Path $ProjectRoot ".tmp"

New-Item -ItemType Directory -Force $ProjectCache, $ProjectTemp | Out-Null

$env:PIP_CACHE_DIR = Join-Path $ProjectCache "pip"
$env:TEMP = $ProjectTemp
$env:TMP = $ProjectTemp

New-Item -ItemType Directory -Force $env:PIP_CACHE_DIR | Out-Null

$VenvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"

if (-not (Test-Path $VenvActivate)) {
    throw "Virtual environment not found: $VenvActivate"
}

# Activate the Python virtual environment
& $VenvActivate

# Discover native runtime directories installed inside the venv.
# Any package under site-packages\<vendor>\*\bin is considered a
# potential runtime/DLL directory and added automatically.
$SitePackages = Join-Path $ProjectRoot ".venv\Lib\site-packages"

if (Test-Path $SitePackages) {
    $RuntimeDirs = Get-ChildItem $SitePackages -Directory -Recurse -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -eq "bin" -and
            $_.FullName -match "\\site-packages\\[^\\]+\\[^\\]+\\bin$"
        } |
        Select-Object -ExpandProperty FullName -Unique

    foreach ($Dir in $RuntimeDirs) {
        if ($env:PATH -notlike "*$Dir*") {
            $env:PATH = "$Dir$([System.IO.Path]::PathSeparator)$env:PATH"
        }
    }
}

# Load .env into the current PowerShell process.
$EnvFile = Join-Path $ProjectRoot ".env"

if (Test-Path $EnvFile) {
    Get-Content $EnvFile |
        Where-Object {
            $_ -match '^\s*[A-Za-z_][A-Za-z0-9_]*\s*=' -and
            $_ -notmatch '^\s*#'
        } |
        ForEach-Object {
            $Name, $Value = $_ -split '=', 2
            $Name = $Name.Trim()
            $Value = $Value.Trim()

            if (
                ($Value.StartsWith('"') -and $Value.EndsWith('"')) -or
                ($Value.StartsWith("'") -and $Value.EndsWith("'"))
            ) {
                $Value = $Value.Substring(1, $Value.Length - 2)
            }

            Set-Item -Path "Env:$Name" -Value $Value
        }
}

# Discover ffplay automatically from PATH first.
$FFplay = Get-Command ffplay.exe -ErrorAction SilentlyContinue

# If it is not already on PATH, search common WinGet package locations.
if (-not $FFplay) {
    $WingetRoot = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"

    if (Test-Path $WingetRoot) {
        $FFplayPath = Get-ChildItem $WingetRoot -Filter "ffplay.exe" -File -Recurse -ErrorAction SilentlyContinue |
            Select-Object -First 1 -ExpandProperty FullName

        if ($FFplayPath) {
            $FFmpegBin = Split-Path $FFplayPath -Parent
            $env:PATH = "$FFmpegBin$([System.IO.Path]::PathSeparator)$env:PATH"
        }
    }
}

Write-Host ""
Write-Host "========================================"
Write-Host " CIMET Voice POC environment loaded"
Write-Host "========================================"
Write-Host "Python:"
python --version

Write-Host ""
Write-Host "Virtual environment:"
Write-Host $env:VIRTUAL_ENV

Write-Host ""
Write-Host "GROQ_API_KEY:"
if ($env:GROQ_API_KEY) {
    Write-Host "Loaded"
} else {
    Write-Host "NOT FOUND"
}

Write-Host ""
Write-Host "FFmpeg:"
$FFplayCheck = Get-Command ffplay.exe -ErrorAction SilentlyContinue
if ($FFplayCheck) {
    Write-Host $FFplayCheck.Source
} else {
    Write-Host "ffplay NOT FOUND"
}

Write-Host ""
Write-Host "Native runtime directories discovered:"
if ($RuntimeDirs) {
    $RuntimeDirs | ForEach-Object { Write-Host " - $_" }
} else {
    Write-Host "None found"
}

Write-Host ""
Write-Host "Environment ready."
Write-Host "========================================"
