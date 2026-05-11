param(
  [string]$BaseUrl = "https://lumen-core.ai",
  [string]$CampaignTag = "ned2026",
  [string]$OutDir = "",
  [switch]$OpenOutput
)

$ErrorActionPreference = "Stop"

function Get-WorkspaceRoot {
  return (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
}

$workspaceRoot = Get-WorkspaceRoot
$reportsRoot = Join-Path $workspaceRoot "reports\NED_Showcase_2026-05-21"

if ([string]::IsNullOrWhiteSpace($OutDir)) {
  $OutDir = Join-Path $reportsRoot "qr_lane_pack"
}

$pagesDir = Join-Path $OutDir "pages"
New-Item -ItemType Directory -Path $pagesDir -Force | Out-Null

$base = $BaseUrl.TrimEnd('/')
$campaign = if ([string]::IsNullOrWhiteSpace($CampaignTag)) { "ned2026" } else { $CampaignTag }

$lanes = @(
  [pscustomobject]@{
    lane = "investor"
    title = "Investor Lane"
    subtitle = "Live diligence path with architecture, health, and snapshot visibility."
    target_path = "/mission_control.html?lane=investor"
    cta_text = "Book a 20-minute diligence call"
  }
  [pscustomobject]@{
    lane = "customer"
    title = "Customer Lane"
    subtitle = "Map your workflow bottlenecks and identify a proof-of-fit deployment."
    target_path = "/mission_control.html?lane=customer"
    cta_text = "Book a 20-minute fit session"
  }
  [pscustomobject]@{
    lane = "partner"
    title = "Partner Lane"
    subtitle = "Define integration boundary, pilot scope, and shared success criteria."
    target_path = "/mission_control.html?lane=partner"
    cta_text = "Book a 20-minute partnership call"
  }
)

$manifest = New-Object System.Collections.Generic.List[object]
$qrMarkdown = New-Object System.Collections.Generic.List[string]

$qrMarkdown.Add("# QR Lane Pack")
$qrMarkdown.Add("")
$qrMarkdown.Add("Generated: $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))")
$qrMarkdown.Add("Campaign tag: $campaign")
$qrMarkdown.Add("")

foreach ($lane in $lanes) {
  $targetUrl = "$base$($lane.target_path)&src=$campaign`_$($lane.lane)_qr"
  $encodedTarget = [uri]::EscapeDataString($targetUrl)
  $qrImageUrl = "https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=$encodedTarget"

  $pagePath = Join-Path $pagesDir ("$($lane.lane).html")
  $relativePagePath = "pages/$($lane.lane).html"
  $pageContent = @"
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LumenCore - $($lane.title)</title>
  <style>
    :root {
      --bg1: #f2efe9;
      --bg2: #dce5dd;
      --ink: #172022;
      --ink-soft: #435059;
      --accent: #c7512c;
      --panel: rgba(255,255,255,0.86);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "Trebuchet MS", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 15% 10%, rgba(199,81,44,0.18), transparent 40%),
        radial-gradient(circle at 85% 20%, rgba(23,32,34,0.12), transparent 36%),
        linear-gradient(150deg, var(--bg1), var(--bg2));
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 24px;
    }
    .card {
      width: min(760px, 100%);
      background: var(--panel);
      border-radius: 18px;
      padding: 28px;
      border: 1px solid rgba(23,32,34,0.08);
      box-shadow: 0 16px 36px rgba(23,32,34,0.14);
    }
    h1 {
      margin: 0 0 10px;
      font-size: clamp(1.5rem, 2.8vw, 2.1rem);
      letter-spacing: 0.01em;
    }
    p {
      margin: 0 0 12px;
      color: var(--ink-soft);
      line-height: 1.5;
    }
    .cta {
      display: inline-block;
      margin-top: 14px;
      background: var(--accent);
      color: #fff;
      text-decoration: none;
      padding: 12px 16px;
      border-radius: 12px;
      font-weight: 600;
      transition: transform 120ms ease, box-shadow 120ms ease;
    }
    .cta:hover {
      transform: translateY(-1px);
      box-shadow: 0 8px 20px rgba(199,81,44,0.25);
    }
    .meta {
      margin-top: 18px;
      font-size: 0.92rem;
      color: var(--ink-soft);
      word-break: break-all;
    }
  </style>
</head>
<body>
  <main class="card">
    <h1>$($lane.title)</h1>
    <p>$($lane.subtitle)</p>
    <p>Primary link: $targetUrl</p>
    <a class="cta" href="$targetUrl">$($lane.cta_text)</a>
    <p class="meta">Campaign source: $campaign | Lane: $($lane.lane)</p>
  </main>
</body>
</html>
"@
  $pageContent | Set-Content -Path $pagePath -Encoding UTF8

  $manifest.Add([pscustomobject]@{
    lane = $lane.lane
    title = $lane.title
    tracked_target_url = $targetUrl
    qr_image_url = $qrImageUrl
    local_page_relative = $relativePagePath
    local_page_absolute = $pagePath
  })

  $qrMarkdown.Add("## $($lane.title)")
  $qrMarkdown.Add("")
  $qrMarkdown.Add("- Tracked target: $targetUrl")
  $qrMarkdown.Add("- QR image: $qrImageUrl")
  $qrMarkdown.Add("- Local page: $relativePagePath")
  $qrMarkdown.Add("- Local page absolute: $pagePath")
  $qrMarkdown.Add("")
}

$manifestPath = Join-Path $OutDir "qr_manifest.json"
$qrLinksPath = Join-Path $OutDir "QR_LINKS.md"
$indexPath = Join-Path $OutDir "index.html"

$manifest | ConvertTo-Json -Depth 8 | Set-Content -Path $manifestPath -Encoding UTF8
$qrMarkdown | Set-Content -Path $qrLinksPath -Encoding UTF8

$indexHtml = @"
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LumenCore QR Lane Pack</title>
  <style>
    body {
      margin: 0;
      font-family: "Segoe UI", "Trebuchet MS", sans-serif;
      background: linear-gradient(180deg, #f7f4ee, #e2ece5);
      color: #1a2224;
      padding: 24px;
    }
    .grid {
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    }
    .lane {
      background: #ffffffd9;
      border-radius: 14px;
      padding: 16px;
      border: 1px solid #d8dfd9;
      box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    }
    img {
      width: 100%;
      max-width: 220px;
      display: block;
      margin: 10px 0;
      border-radius: 10px;
      border: 1px solid #d8dfd9;
    }
    a { color: #8f3114; word-break: break-all; }
  </style>
</head>
<body>
  <h1>LumenCore QR Lane Pack</h1>
  <p>Campaign tag: $campaign</p>
  <div class="grid">
"@

foreach ($item in $manifest) {
  $indexHtml += @"
    <section class="lane">
      <h2>$($item.title)</h2>
      <a href="$($item.tracked_target_url)">$($item.tracked_target_url)</a>
      <img src="$($item.qr_image_url)" alt="$($item.title) QR code"/>
      <p><a href="$($item.local_page_relative)">Open local lane page</a></p>
    </section>
"@
}

$indexHtml += @"
  </div>
</body>
</html>
"@

$indexHtml | Set-Content -Path $indexPath -Encoding UTF8

Write-Host ""
Write-Host "NED QR lane pack generated"
Write-Host "- output dir:   $OutDir"
Write-Host "- manifest:     $manifestPath"
Write-Host "- links file:   $qrLinksPath"
Write-Host "- index page:   $indexPath"

if ($OpenOutput) {
  Invoke-Item -Path $OutDir
}
