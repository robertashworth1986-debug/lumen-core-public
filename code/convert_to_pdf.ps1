$htmlFile = "c:\Users\Novac\iCloudDrive\Lumen_nova-core master-dos\MASTER_PITCH_OPTIMIZED.html"
$pdfFile = "c:\Users\Novac\iCloudDrive\Lumen_nova-core master-dos\MASTER_PITCH_OPTIMIZED.pdf"

Write-Host "Converting HTML to PDF..."

# Try Edge
$edgePath = "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path $edgePath)) {
    $edgePath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
}

if (Test-Path $edgePath) {
    Write-Host "Using Microsoft Edge..."
    $args = "--headless", "--disable-gpu", "--print-to-pdf=$pdfFile", "file://$htmlFile"
    & $edgePath $args
    Start-Sleep -Seconds 4
}

if (Test-Path $pdfFile) {
    Write-Host "✓ PDF created!"
    Write-Host "File: $pdfFile"
    Start-Process $pdfFile
    exit 0
}

# Try Chrome
$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chromePath)) {
    $chromePath = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
}

if (Test-Path $chromePath) {
    Write-Host "Trying Google Chrome..."
    $args = "--headless", "--disable-gpu", "--print-to-pdf=$pdfFile", "file://$htmlFile"
    & $chromePath $args
    Start-Sleep -Seconds 4
}

if (Test-Path $pdfFile) {
    Write-Host "✓ PDF created with Chrome!"
    Start-Process $pdfFile
    exit 0
}

Write-Host "⚠ Could not auto-create PDF"
Write-Host ""
Write-Host "HTML file ready: $htmlFile"
Write-Host "To convert manually:"
Write-Host "1. Open HTML file in browser"
Write-Host "2. Press Ctrl+P"
Write-Host "3. Select 'Save as PDF'"
