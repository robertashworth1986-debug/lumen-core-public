# PowerShell script to automate all health, proof, and compliance checks on a schedule
# Save as automate_luma_stack.ps1 and schedule via Windows Task Scheduler

$venvPython = "c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe"
$dashboardPath = "c:/LumaTrader/INSTITUTIONAL_STACK_V2/dashboard"

# Run API key status update
Write-Host "Updating API key status..."
& $venvPython "$dashboardPath/update_api_key_status.py"

# Run orchestrator watchdog
Write-Host "Running orchestrator watchdog..."
& $venvPython "$dashboardPath/orchestrator_watchdog.py"

# Run proof pack/validation generation
Write-Host "Generating validation proof pack..."
& $venvPython "$dashboardPath/generate_validation_proof.py"

# Run compliance/MVP progress automation
Write-Host "Updating compliance/MVP progress..."
& $venvPython "$dashboardPath/update_compliance_progress.py"

Write-Host "All LumaTrader stack health/compliance checks complete."
