$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$CheckovScript = Join-Path $ProjectRoot ".venv\Scripts\checkov"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

$InsecureTerraform = Join-Path $ProjectRoot "terraform\insecure"
$RemediatedTerraform = Join-Path $ProjectRoot "terraform\remediated"

$RawDirectory = Join-Path $ProjectRoot "data\raw"
$NormalizedDirectory = Join-Path $ProjectRoot "data\normalized"
$DatabasePath = Join-Path $ProjectRoot "data\cloudguard.db"

$InsecureRaw = Join-Path $RawDirectory "insecure-findings.json"
$RemediatedRaw = Join-Path $RawDirectory "remediated-findings.json"

$InsecureNormalized = Join-Path $NormalizedDirectory "insecure-findings.json"
$RemediatedNormalized = Join-Path $NormalizedDirectory "remediated-findings.json"

function Write-Step {
    param (
        [string]$Message
    )

    Write-Host ""
    Write-Host "==================================================" -ForegroundColor DarkGray
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "==================================================" -ForegroundColor DarkGray
}

function Assert-PathExists {
    param (
        [string]$PathToCheck,
        [string]$Description
    )

    if (-not (Test-Path $PathToCheck)) {
        throw "$Description was not found: $PathToCheck"
    }
}

function Invoke-CheckovScan {
    param (
        [string]$TerraformDirectory,
        [string]$OutputPath,
        [string]$EnvironmentName
    )

    Write-Host "Scanning $EnvironmentName Terraform configuration..." `
        -ForegroundColor Yellow

    if (Test-Path $OutputPath) {
        $existingItem = Get-Item $OutputPath

        if ($existingItem.PSIsContainer) {
            Remove-Item $OutputPath -Recurse -Force
        }
        else {
            Remove-Item $OutputPath -Force
        }
    }

    $stderrPath = Join-Path $RawDirectory "$EnvironmentName-checkov-stderr.txt"

    if (Test-Path $stderrPath) {
        Remove-Item $stderrPath -Force
    }

    $checkovOutput = & $Python `
        $CheckovScript `
        -d $TerraformDirectory `
        --output json `
        2> $stderrPath |
    Out-String


    $checkovExitCode = $LASTEXITCODE

    [System.IO.File]::WriteAllText(
        $OutputPath,
        $checkovOutput,
        [System.Text.UTF8Encoding]::new($false)
    )

    if (-not (Test-Path $OutputPath)) {
        throw "Checkov did not create an output file for $EnvironmentName."
    }

    $outputLength = (Get-Item $OutputPath).Length

    if ($outputLength -eq 0) {
        throw "Checkov created an empty output file for $EnvironmentName."
    }

    if ($checkovExitCode -ne 0) {
        Write-Host (
            "Checkov returned exit code $checkovExitCode for $EnvironmentName. " +
            "This is expected when failed checks are found."
        ) -ForegroundColor DarkYellow
    }
    else {
        Write-Host "Checkov completed without failed checks." `
            -ForegroundColor Green
    }

    Write-Host "Raw output: $OutputPath" -ForegroundColor Gray
}

function Invoke-Normalizer {
    param (
        [string]$InputPath,
        [string]$OutputPath,
        [string]$EnvironmentName
    )

    Write-Host "Normalizing $EnvironmentName findings..." `
        -ForegroundColor Yellow

    & $Python `
    (Join-Path $ProjectRoot "scanners\normalize_checkov.py") `
        --input $InputPath `
        --output $OutputPath `
        --environment $EnvironmentName

    if ($LASTEXITCODE -ne 0) {
        throw "Normalization failed for $EnvironmentName."
    }

    Assert-PathExists $OutputPath `
        "Normalized findings for $EnvironmentName"

    Write-Host "Normalized output: $OutputPath" `
        -ForegroundColor Gray
}

function Invoke-DatabaseSeed {
    param (
        [string]$InputPath,
        [string]$EnvironmentName
    )

    Write-Host "Loading $EnvironmentName findings into SQLite..." `
        -ForegroundColor Yellow

    & $Python `
    (Join-Path $ProjectRoot "dashboard\seed_database.py") `
        --input $InputPath `
        --environment $EnvironmentName `
        --database $DatabasePath

    if ($LASTEXITCODE -ne 0) {
        throw "Database seeding failed for $EnvironmentName."
    }
}

Write-Step "CloudGuard CSPM pipeline starting"

Assert-PathExists $CheckovScript "Checkov script"
Assert-PathExists $Python "Project Python executable"
Assert-PathExists $InsecureTerraform "Insecure Terraform directory"
Assert-PathExists $RemediatedTerraform "Remediated Terraform directory"

New-Item -ItemType Directory -Force -Path $RawDirectory | Out-Null
New-Item -ItemType Directory -Force -Path $NormalizedDirectory | Out-Null

Write-Step "1. Running Checkov scans"

Invoke-CheckovScan `
    -TerraformDirectory $InsecureTerraform `
    -OutputPath $InsecureRaw `
    -EnvironmentName "insecure"

Invoke-CheckovScan `
    -TerraformDirectory $RemediatedTerraform `
    -OutputPath $RemediatedRaw `
    -EnvironmentName "remediated"

Write-Step "2. Normalizing Checkov findings"

Invoke-Normalizer `
    -InputPath $InsecureRaw `
    -OutputPath $InsecureNormalized `
    -EnvironmentName "insecure"

Invoke-Normalizer `
    -InputPath $RemediatedRaw `
    -OutputPath $RemediatedNormalized `
    -EnvironmentName "remediated"

Write-Step "3. Rebuilding SQLite database"

if (Test-Path $DatabasePath) {
    Remove-Item $DatabasePath -Force
    Write-Host "Removed previous database." -ForegroundColor Gray
}

Invoke-DatabaseSeed `
    -InputPath $InsecureNormalized `
    -EnvironmentName "insecure"

Invoke-DatabaseSeed `
    -InputPath $RemediatedNormalized `
    -EnvironmentName "remediated"

Write-Step "4. Verifying generated artifacts"

Assert-PathExists $InsecureRaw "Insecure raw findings"
Assert-PathExists $RemediatedRaw "Remediated raw findings"
Assert-PathExists $InsecureNormalized "Insecure normalized findings"
Assert-PathExists $RemediatedNormalized "Remediated normalized findings"
Assert-PathExists $DatabasePath "SQLite database"

Write-Host "Generated files:" -ForegroundColor Green
Write-Host "  $InsecureRaw"
Write-Host "  $RemediatedRaw"
Write-Host "  $InsecureNormalized"
Write-Host "  $RemediatedNormalized"
Write-Host "  $DatabasePath"

Write-Step "CloudGuard CSPM pipeline completed successfully"

Write-Host "The Streamlit dashboard can now be started with:" `
    -ForegroundColor Green
Write-Host ".\.venv\Scripts\streamlit.exe run .\dashboard\app.py"
