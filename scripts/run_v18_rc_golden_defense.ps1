# V18-RC Golden Defense Case Runner
# Usage: powershell -ExecutionPolicy Bypass -File scripts/run_v18_rc_golden_defense.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

Write-Host "=== V18-RC Golden Defense Case Runner ===" -ForegroundColor Cyan
Write-Host "Project Root: $ProjectRoot"
Write-Host ""

# Step 1: Verify input files exist
Write-Host "[1/6] Verifying input files..." -ForegroundColor Yellow
$inputDir = "tests/golden_cases/defense_case_001/input"
$requiredFiles = @("民事起诉状.txt", "借款协议.txt", "银行转账凭证.txt")
foreach ($f in $requiredFiles) {
    $path = Join-Path $inputDir $f
    if (-not (Test-Path $path)) {
        Write-Host "  [FAIL] Missing: $f" -ForegroundColor Red
        exit 1
    }
    Write-Host "  [OK] $f"
}

# Step 2: Run pipeline
Write-Host ""
Write-Host "[2/6] Running analysis pipeline..." -ForegroundColor Yellow
$outputDir = "outputs/golden_defense_case"
python -m core.runner analyze --input $inputDir --identity "被诉方" --goal "应诉答辩" --out $outputDir
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [FAIL] Pipeline failed" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Pipeline completed"

# Step 3: Run quality gate
Write-Host ""
Write-Host "[3/6] Running quality gate..." -ForegroundColor Yellow
python -m core.runner selfcheck --case $outputDir
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [FAIL] Quality gate failed" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Quality gate passed"

# Step 4: Run acceptance test
Write-Host ""
Write-Host "[4/6] Running acceptance test..." -ForegroundColor Yellow
python scripts/accept_v18_delivery.py $outputDir
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [FAIL] Acceptance test failed" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Acceptance test passed"

# Step 5: Run defense quality gate (via Python script)
Write-Host ""
Write-Host "[5/6] Running defense quality gate..." -ForegroundColor Yellow
python scripts/run_v18_rc_golden_defense.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [FAIL] Defense quality gate failed" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Defense quality gate passed"

# Step 6: Verify outputs
Write-Host ""
Write-Host "[6/6] Verifying outputs..." -ForegroundColor Yellow
$customerDir = Join-Path $outputDir "customer"
$expectedFiles = @("*.docx", "*.pdf", "*.zip")
foreach ($pattern in $expectedFiles) {
    $files = Get-ChildItem -Path $customerDir -Filter $pattern -ErrorAction SilentlyContinue
    if ($files) {
        Write-Host "  [OK] Found $($files.Count) $pattern file(s)"
    } else {
        Write-Host "  [FAIL] No $pattern files found" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "=== Golden Defense Case PASSED ===" -ForegroundColor Green
Write-Host "Output directory: $outputDir"
exit 0
