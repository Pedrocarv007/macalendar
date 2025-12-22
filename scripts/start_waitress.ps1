param(
    [string]$Listen = "127.0.0.1:6005",
    [int]$Threads = 8,
    [string]$EnvFile = "$PSScriptRoot/../.env"
)

# Load .env key=value into environment (simple parser: ignores blanks and # comments)
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^(\s*#|\s*$)') { return }
        $parts = $_ -split '=', 2
        if ($parts.Count -eq 2) {
            $key = $parts[0].Trim()
            $val = $parts[1].Trim()
            if ($key) {
                Set-Item -Path Env:$key -Value $val
            }
        }
    }
}

# Ensure venv is active
$venvActivate = "$PSScriptRoot/../.venv/Scripts/Activate.ps1"
if (-not (Test-Path $venvActivate)) {
    Write-Error "Virtualenv not found at $venvActivate"
    exit 1
}
. $venvActivate

# Required app settings
if (-not $env:RUNNING_ON_IIS) { $env:RUNNING_ON_IIS = "1" }
if (-not $env:FLASK_CONFIG) { $env:FLASK_CONFIG = "production" }
$env:HOST = ($Listen -split ':')[0]
$env:PORT = ($Listen -split ':')[1]

Write-Host "Starting Waitress on $Listen with $Threads threads..."
waitress-serve --listen=$Listen --threads=$Threads run:app
