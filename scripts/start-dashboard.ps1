param(
    [string]$Python = "python",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $projectRoot "src"

# Native Windows Python uses the OS trust store. Some MSYS builds need a CA file.
$needsCertificate = & $Python -c "import ssl; print(int(not hasattr(ssl, 'enum_certificates') and ssl.get_default_verify_paths().cafile is None))"
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.10+ is required. Pass -Python with the path of your installed interpreter."
}
if ($needsCertificate -eq "1" -and -not $env:SSL_CERT_FILE) {
    $gitCommand = Get-Command git -ErrorAction SilentlyContinue
    if ($gitCommand) {
        $gitRoot = Split-Path -Parent (Split-Path -Parent $gitCommand.Source)
        $certificate = Join-Path $gitRoot "usr\ssl\certs\ca-bundle.crt"
        if (Test-Path -LiteralPath $certificate) {
            $env:SSL_CERT_FILE = $certificate
        }
    }
}

Push-Location $projectRoot
try {
    & $Python -m risk_assessment.server --port $Port
} finally {
    Pop-Location
}
