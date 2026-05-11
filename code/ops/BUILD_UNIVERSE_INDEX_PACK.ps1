param(
    [string]$ScanRoot = "C:\LumaTrader\out\ops\context_scan_20260510_200619",
    [string]$UniverseRoot
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($UniverseRoot)) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $UniverseRoot = "C:\LumaTrader\out\ops\universe_map_$stamp"
}

New-Item -ItemType Directory -Path $UniverseRoot -Force | Out-Null

$cFiles = Join-Path $ScanRoot "c_drive_all_files.txt"
$iFiles = Join-Path $ScanRoot "icloud_all_files.txt"
$inputFiles = @($cFiles, $iFiles) | Where-Object { Test-Path $_ }
if ($inputFiles.Count -eq 0) {
    throw "No input manifests found under $ScanRoot"
}

$visualExt = @(".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".tif", ".tiff", ".heic", ".stl", ".obj", ".glb", ".fbx")
$docExt = @(".pdf", ".doc", ".docx", ".md", ".txt", ".ppt", ".pptx", ".rtf")
$dataExt = @(".csv", ".json", ".jsonl", ".parquet", ".feather", ".xlsx", ".tsv")
$scriptExt = @(".py", ".ps1", ".sh", ".js", ".ts", ".cs", ".ipynb", ".yaml", ".yml", ".toml", ".ini", ".conf", ".cfg")

$patternBlueprint = "blueprint|motherboard|honeycomb|battery|robot|haptic|dome|flowform|luman?spiral|etherframe|lumenshell|aetherreach|echolock|whitehole|digital twin|xr|ar|vr|cad|cymatic"
$patternWhitepaper = "whitepaper|white paper|onepager|technical overview|overview|paper|specification|patent|non-provisional|uspto|application"
$patternPilot = "pilot|brief|proposal|capability statement|sbir|darpa|doe|nsf|grant|federal brief|investor brief|institutional review"
$patternProof = "proof|frozen delta|chain_of_custody|sha256|audit|ledger|readiness|evidence|txid|execution_events|reconciliation|heartbeat"
$patternDashboard = "dashboard|mission_control|investor_command_room|wallboard|quant_lab|scenario_mission|grants|luma_experience"
$patternQuant = "quant_lab|mission_control|investor_command_room|kraken_execution_dashboard|dashboard_portal|luma_experience|scenario_mission"

$engineRules = @(
    @{ Name = "LumaTrader Institutional"; Pattern = "lumatrader|institutional_stack_v2|execution_orchestrator|live_executor|kraken_execution|quant_lab|mission_control"; Lane = "Trading" },
    @{ Name = "Kraken Trader LumaSniper"; Pattern = "kraken|sniper|symbol registry|kill switch|paper|live mode"; Lane = "Trading" },
    @{ Name = "LumenGov Grant Factory"; Pattern = "lumengov|grant|sbir|darpa|doe|nsf|capability statement|federal"; Lane = "Gov" },
    @{ Name = "Infrastructure Outage Prevention"; Pattern = "drift|baseline|frozen delta|chain_of_custody|uptime|integrity|reconciliation"; Lane = "Infrastructure" },
    @{ Name = "LumaScout Digital Scout"; Pattern = "lumascout|scout|creator|artist|talent|momentum"; Lane = "Scout" },
    @{ Name = "Sports Signal Engine"; Pattern = "sports|odds|book|dk_|draftkings|bet|edge"; Lane = "Sports" },
    @{ Name = "CrowdFunding Engine"; Pattern = "crowdfunding|kickstarter|indiegogo|campaign"; Lane = "Crowdfunding" },
    @{ Name = "Cyber Digital Forensics"; Pattern = "forensic|cyber|incident|triage|court"; Lane = "Cyber" },
    @{ Name = "Identity EchoForm Digital Twin"; Pattern = "identity|echoform|digital twin|legacy|persona|memory model"; Lane = "Identity" },
    @{ Name = "Unity XR Luma Live Command"; Pattern = "unity|xr|ar|vr|haptic|dome|holographic|scene cue"; Lane = "XR" },
    @{ Name = "Smart City Telecom"; Pattern = "smart city|telecom|iot|edge compute|sensor"; Lane = "Infra-Energy" },
    @{ Name = "FlowForm Hardware Geometry"; Pattern = "flowform|motherboard|honeycomb|battery|geometry|cymatic|spiral"; Lane = "Hardware" },
    @{ Name = "Energy Nuclear Harmonization"; Pattern = "energy|nuclear|grid|solar|fuel|eia|utility|coal|weather"; Lane = "Infra-Energy" },
    @{ Name = "World Model Cross-Sector"; Pattern = "worldmodel|world model|cross-sector|scenario|simulation|monte carlo"; Lane = "World-Model" },
    @{ Name = "LumaCore Orchestrator"; Pattern = "orchestrator|meta_router|master|kernel|bounded_infinity|luma_experience_gateway"; Lane = "Kernel" }
)

function Get-EngineInfo {
    param([string]$LowerPath)
    foreach ($r in $engineRules) {
        if ($LowerPath -match $r.Pattern) {
            return @{ Name = $r.Name; Lane = $r.Lane }
        }
    }
    return @{ Name = "Unclassified"; Lane = "Unclassified" }
}

function Escape-Csv {
    param([string]$Value)
    if ($null -eq $Value) { return '""' }
    $escaped = $Value -replace '"', '""'
    return '"' + $escaped + '"'
}

function New-Writer {
    param([string]$Path, [string]$Header)
    $enc = New-Object System.Text.UTF8Encoding($false)
    $w = New-Object System.IO.StreamWriter($Path, $false, $enc)
    $w.WriteLine($Header)
    return $w
}

function Write-CsvLine {
    param(
        [Parameter(Mandatory = $true)]$Writer,
        [Parameter(Mandatory = $true)][string[]]$Fields
    )
    $Writer.WriteLine(($Fields -join ','))
}

$paths = @{
    Visual = Join-Path $UniverseRoot "visual_assets_index.csv"
    Blueprint = Join-Path $UniverseRoot "blueprint_assets_index.csv"
    Whitepaper = Join-Path $UniverseRoot "whitepapers_index.csv"
    Pilot = Join-Path $UniverseRoot "pilot_briefs_index.csv"
    Dashboard = Join-Path $UniverseRoot "dashboards_index.csv"
    Proof = Join-Path $UniverseRoot "proof_artifacts_index.csv"
    Execution = Join-Path $UniverseRoot "execution_core_index.csv"
    Dataset = Join-Path $UniverseRoot "datasets_index.csv"
    Quant = Join-Path $UniverseRoot "quant_lab_suite_manifest.csv"
}

$writers = @{}
$writers.Visual = New-Writer -Path $paths.Visual -Header "Path,Engine,Lane,Source"
$writers.Blueprint = New-Writer -Path $paths.Blueprint -Header "Path,Engine,Lane,Source"
$writers.Whitepaper = New-Writer -Path $paths.Whitepaper -Header "Path,Engine,Lane,Source"
$writers.Pilot = New-Writer -Path $paths.Pilot -Header "Path,Engine,Lane,Source"
$writers.Dashboard = New-Writer -Path $paths.Dashboard -Header "Path,Engine,Lane,Source"
$writers.Proof = New-Writer -Path $paths.Proof -Header "Path,Engine,Lane,Source"
$writers.Execution = New-Writer -Path $paths.Execution -Header "Path,Engine,Lane,Source"
$writers.Dataset = New-Writer -Path $paths.Dataset -Header "Path,Engine,Lane,Source"
$writers.Quant = New-Writer -Path $paths.Quant -Header "Section,Path,Engine,Lane,Source"

$counts = [ordered]@{
    visual_assets_index = 0
    blueprint_assets_index = 0
    whitepapers_index = 0
    pilot_briefs_index = 0
    dashboards_index = 0
    proof_artifacts_index = 0
    execution_core_index = 0
    datasets_index = 0
    quant_lab_suite_manifest = 0
}

$engineSummary = @{}
foreach ($r in $engineRules) {
    $engineSummary[$r.Name] = [ordered]@{
        lane = $r.Lane
        visuals = 0
        blueprints = 0
        whitepapers = 0
        pilot_briefs = 0
        dashboards = 0
        proofs = 0
        execution_core = 0
        datasets = 0
        quant_refs = 0
    }
}
$engineSummary["Unclassified"] = [ordered]@{
    lane = "Unclassified"
    visuals = 0
    blueprints = 0
    whitepapers = 0
    pilot_briefs = 0
    dashboards = 0
    proofs = 0
    execution_core = 0
    datasets = 0
    quant_refs = 0
}

try {
    foreach ($mf in $inputFiles) {
        $source = [System.IO.Path]::GetFileName($mf)
        foreach ($p in [System.IO.File]::ReadLines($mf)) {
            if ([string]::IsNullOrWhiteSpace($p)) { continue }
            $lp = $p.ToLowerInvariant()
            $ext = [System.IO.Path]::GetExtension($lp)
            $engine = Get-EngineInfo -LowerPath $lp
            $engineName = $engine.Name
            $lane = $engine.Lane

            $isVisual = $visualExt -contains $ext
            $isBlueprint = $isVisual -and ($lp -match $patternBlueprint)
            $isWhitepaper = ($docExt -contains $ext) -and ($lp -match $patternWhitepaper)
            $isPilot = ($docExt -contains $ext) -and ($lp -match $patternPilot)
            $isDashboard = ($lp -match $patternDashboard) -and ($ext -in @(".html", ".md", ".py", ".json", ".js", ".css"))
            $isProof = $lp -match $patternProof
            $isExec = ($scriptExt -contains $ext) -and ($lp -match "execution_orchestrator|live_executor|order_router|liquidity_guard|risk_kernel|rl_policy|signal_gate|rolling_capital|harmonic_signal_connector|runtime_control")
            $isDataset = ($dataExt -contains $ext) -and ($lp -match "backtest|walk_forward|monte|simulation|dataset|ohlc|equity|leaderboard|performance|roi|trades|signals|eia|nasa|weather|utility|grid|nuclear|sports")
            $isQuant = $lp -match $patternQuant

            if ($isVisual) {
                Write-CsvLine -Writer $writers.Visual -Fields @((Escape-Csv $p), (Escape-Csv $engineName), (Escape-Csv $lane), (Escape-Csv $source))
                $counts.visual_assets_index++
                $engineSummary[$engineName].visuals++
            }
            if ($isBlueprint) {
                Write-CsvLine -Writer $writers.Blueprint -Fields @((Escape-Csv $p), (Escape-Csv $engineName), (Escape-Csv $lane), (Escape-Csv $source))
                $counts.blueprint_assets_index++
                $engineSummary[$engineName].blueprints++
            }
            if ($isWhitepaper) {
                Write-CsvLine -Writer $writers.Whitepaper -Fields @((Escape-Csv $p), (Escape-Csv $engineName), (Escape-Csv $lane), (Escape-Csv $source))
                $counts.whitepapers_index++
                $engineSummary[$engineName].whitepapers++
            }
            if ($isPilot) {
                Write-CsvLine -Writer $writers.Pilot -Fields @((Escape-Csv $p), (Escape-Csv $engineName), (Escape-Csv $lane), (Escape-Csv $source))
                $counts.pilot_briefs_index++
                $engineSummary[$engineName].pilot_briefs++
            }
            if ($isDashboard) {
                Write-CsvLine -Writer $writers.Dashboard -Fields @((Escape-Csv $p), (Escape-Csv $engineName), (Escape-Csv $lane), (Escape-Csv $source))
                $counts.dashboards_index++
                $engineSummary[$engineName].dashboards++
            }
            if ($isProof) {
                Write-CsvLine -Writer $writers.Proof -Fields @((Escape-Csv $p), (Escape-Csv $engineName), (Escape-Csv $lane), (Escape-Csv $source))
                $counts.proof_artifacts_index++
                $engineSummary[$engineName].proofs++
            }
            if ($isExec) {
                Write-CsvLine -Writer $writers.Execution -Fields @((Escape-Csv $p), (Escape-Csv $engineName), (Escape-Csv $lane), (Escape-Csv $source))
                $counts.execution_core_index++
                $engineSummary[$engineName].execution_core++
            }
            if ($isDataset) {
                Write-CsvLine -Writer $writers.Dataset -Fields @((Escape-Csv $p), (Escape-Csv $engineName), (Escape-Csv $lane), (Escape-Csv $source))
                $counts.datasets_index++
                $engineSummary[$engineName].datasets++
            }

            if ($isQuant) {
                $section = "Command Center Board"
                if ($isWhitepaper) { $section = "White Papers" }
                elseif ($isPilot) { $section = "Pilot Briefs" }
                elseif ($isBlueprint) { $section = "Visual IP and Blueprints" }
                elseif ($isVisual) { $section = "Visuals and Graphics" }
                elseif ($isProof) { $section = "Proof and Frozen Delta" }
                elseif ($isDataset) { $section = "Datasets and Runs" }
                Write-CsvLine -Writer $writers.Quant -Fields @((Escape-Csv $section), (Escape-Csv $p), (Escape-Csv $engineName), (Escape-Csv $lane), (Escape-Csv $source))
                $counts.quant_lab_suite_manifest++
                $engineSummary[$engineName].quant_refs++
            }
        }
    }
}
finally {
    foreach ($w in $writers.Values) { $w.Dispose() }
}

$summaryPath = Join-Path $UniverseRoot "universe_index_summary.json"
$engineSummaryPath = Join-Path $UniverseRoot "engine_product_map.json"
$quantMd = Join-Path $UniverseRoot "quant_lab_suite_manifest.md"

$counts | ConvertTo-Json -Depth 4 | Set-Content -Path $summaryPath -Encoding UTF8
$engineSummary | ConvertTo-Json -Depth 8 | Set-Content -Path $engineSummaryPath -Encoding UTF8

$md = @()
$md += "# Quant Lab Universe Suite Manifest"
$md += ""
$md += "Generated UTC: $(Get-Date).ToUniversalTime().ToString('u')"
$md += "Input manifests: $($inputFiles -join ', ')"
$md += ""
$md += "## Section Counts"
foreach ($k in $counts.Keys) {
    $md += ("- {0}: {1}" -f $k, $counts[$k])
}
$md += ""
$md += "## Lane Separation Guard"
$md += "- Trading and Infra-Energy are tagged by lane in every index row."
$md += "- Use Lane column to prevent mixing trading Sharpe/edge data with infra-energy optimization datasets."
$md += ""
$md += "## Key Output Files"
$md += "- visual_assets_index.csv"
$md += "- blueprint_assets_index.csv"
$md += "- whitepapers_index.csv"
$md += "- pilot_briefs_index.csv"
$md += "- dashboards_index.csv"
$md += "- proof_artifacts_index.csv"
$md += "- execution_core_index.csv"
$md += "- datasets_index.csv"
$md += "- quant_lab_suite_manifest.csv"
$md += "- engine_product_map.json"

$md | Set-Content -Path $quantMd -Encoding UTF8

Write-Output "UNIVERSE_ROOT=$UniverseRoot"
Get-ChildItem -LiteralPath $UniverseRoot -File | Select-Object Name, Length, LastWriteTime | Sort-Object Name | Format-Table -AutoSize
Write-Output "--- COUNTS"
$counts.GetEnumerator() | Sort-Object Name | Format-Table Name, Value -AutoSize
