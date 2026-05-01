$htmlFile = "c:\Users\Novac\iCloudDrive\Lumen_nova-core master-dos\MASTER_PITCH_OPTIMIZED.html"
$pdfFile = "c:\Users\Novac\iCloudDrive\Lumen_nova-core master-dos\MASTER_PITCH_OPTIMIZED.pdf"

Write-Host "Converting HTML to PDF using Microsoft Edge..."
$edgePath = "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path $edgePath)) {
    $edgePath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
}

if (Test-Path $edgePath) {
    $edgeArgs = @(
        "--headless",
        "--disable-gpu",
        "--print-to-pdf=$pdfFile",
        "file://$htmlFile"
    )
    
    & $edgePath @edgeArgs
    Start-Sleep -Seconds 4
    
    if (Test-Path $pdfFile) {
        Write-Host "✓ PDF created successfully!"
        Write-Host "File: $pdfFile"
        Write-Host "Size: $(((Get-Item $pdfFile).Length / 1KB).ToString('F0')) KB"
        Start-Process $pdfFile
    } else {
        Write-Host "⚠ PDF not created. Trying alternative..."
    }
} else {
    Write-Host "⚠ Microsoft Edge not found"
}

# Try Chrome as fallback
if (-not (Test-Path $pdfFile)) {
    Write-Host "Trying Google Chrome..."
    $chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
    if (-not (Test-Path $chromePath)) {
        $chromePath = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    }
    
    if (Test-Path $chromePath) {
        $chromeArgs = @(
            "--headless",
            "--disable-gpu",
            "--print-to-pdf=$pdfFile",
            "file://$htmlFile"
        )
        
        & $chromePath @chromeArgs
        Start-Sleep -Seconds 4
        
        if (Test-Path $pdfFile) {
            Write-Host "✓ PDF created with Chrome!"
            Start-Process $pdfFile
        }
    }
}
