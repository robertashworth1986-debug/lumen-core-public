<#
.SYNOPSIS
  Build a safe, repo-local session packet from installed Codex plugins and MCP hints.

.DESCRIPTION
  This script is intended for the Windows operator machine where Codex plugins live under
  $HOME\.codex. It inventories plugin metadata files, MCP config hints, and obvious
  browser-control plugin names, then writes a non-secret manifest and markdown packet into
  the current LumenCore repo. It does not copy plugin source code, tokens, browser cookies,
  MFA data, or account credentials.
#>

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "=== LumenCore Codex Plugin Session Packet Builder ===" -ForegroundColor Cyan
Write-Host "Inventories local Codex plugins/MCP hints into this repo without copying secrets." -ForegroundColor Yellow
Write-Host ""

$RepoRoot = (Get-Location).Path
if (-not (Test-Path (Join-Path $RepoRoot "README.md"))) {
  $RepoRootInput = Read-Host "Run this from the LumenCore repo root, or paste the repo root path"
  $RepoRoot = $RepoRootInput.Trim('"')
}

if (-not (Test-Path (Join-Path $RepoRoot "README.md"))) {
  Write-Host "Repo root not found or README.md missing: $RepoRoot" -ForegroundColor Red
  exit 1
}

$CodexRoot = Join-Path $HOME ".codex"
$SearchRoots = @(
  $CodexRoot,
  (Join-Path $CodexRoot ".tmp\plugins"),
  (Join-Path $CodexRoot "plugins\cache")
) | Where-Object { Test-Path $_ } | Select-Object -Unique

$PluginFiles = @()
foreach ($Root in $SearchRoots) {
  $PluginFiles += Get-ChildItem -Path $Root -Recurse -Force -File -ErrorAction SilentlyContinue |
    Where-Object {
      $_.Name -in @(".codex-plugin", "plugin.json", "mcp.json", "SKILL.md") -or
      $_.FullName -match "(?i)(playwright|browser|computer|desktop|mcp|operator|bridge|grants|gov|openai-developers)"
    }
}

$PluginFiles = $PluginFiles | Sort-Object FullName -Unique

$Entries = foreach ($File in $PluginFiles) {
  $Relative = $File.FullName
  if ($Relative.StartsWith($CodexRoot)) {
    $Relative = $Relative.Substring($CodexRoot.Length).TrimStart('\')
  }

  $Kind = switch -Regex ($File.FullName) {
    "(?i)mcp\.json$" { "mcp_config"; break }
    "(?i)\.codex-plugin$" { "codex_plugin_marker"; break }
    "(?i)plugin\.json$" { "plugin_manifest"; break }
    "(?i)SKILL\.md$" { "skill_instructions"; break }
    default { "matched_file" }
  }

  $Lane = if ($File.FullName -match "(?i)(playwright|browser|computer|desktop|operator)") {
    "browser_or_computer_control_candidate"
  } elseif ($File.FullName -match "(?i)(mcp|bridge)") {
    "mcp_or_bridge_candidate"
  } elseif ($File.FullName -match "(?i)(grant|grants|gov|sam|sbir)") {
    "grant_submission_candidate"
  } else {
    "general_plugin"
  }

  [pscustomobject]@{
    kind = $Kind
    lane = $Lane
    name = $File.BaseName
    path = $File.FullName
    relative_to_codex = $Relative
    last_write_time = $File.LastWriteTime.ToString("o")
    bytes = $File.Length
  }
}

$Summary = [ordered]@{
  generated_at = (Get-Date).ToUniversalTime().ToString("o")
  repo_root = $RepoRoot
  codex_root = $CodexRoot
  total_matches = @($Entries).Count
  browser_or_computer_control_candidates = @($Entries | Where-Object lane -eq "browser_or_computer_control_candidate").Count
  mcp_or_bridge_candidates = @($Entries | Where-Object lane -eq "mcp_or_bridge_candidate").Count
  grant_submission_candidates = @($Entries | Where-Object lane -eq "grant_submission_candidate").Count
}

$Payload = [ordered]@{
  summary = $Summary
  safety = [ordered]@{
    copied_plugin_source = $false
    copied_credentials = $false
    copied_browser_cookies = $false
    final_grant_submission_automation = $false
    note = "This packet records plugin/MCP paths only. It does not attach tools to a hosted session by itself."
  }
  entries = @($Entries)
}

$DataDir = Join-Path $RepoRoot "data"
$DocsDir = Join-Path $RepoRoot "docs"
New-Item -ItemType Directory -Force -Path $DataDir, $DocsDir | Out-Null

$JsonPath = Join-Path $DataDir "local_codex_plugin_session_manifest.json"
$MdPath = Join-Path $DocsDir "LOCAL_CODEX_PLUGIN_SESSION_PACKET.md"

$Payload | ConvertTo-Json -Depth 8 | Set-Content -Path $JsonPath -Encoding UTF8

$TopBrowser = @($Entries | Where-Object lane -eq "browser_or_computer_control_candidate" | Select-Object -First 40)
$TopMcp = @($Entries | Where-Object lane -eq "mcp_or_bridge_candidate" | Select-Object -First 40)
$TopGrant = @($Entries | Where-Object lane -eq "grant_submission_candidate" | Select-Object -First 40)

$Markdown = @"
# Local Codex Plugin Session Packet

Generated: $($Summary.generated_at)

This packet inventories the operator's local Codex plugin and MCP-related paths so a compatible Codex/MCP session can be rehydrated with the right browser-control, Playwright, grant, and bridge plugins. It is a **path and capability map**, not a credential export.

## Safety Boundary

- Does not copy plugin source code into the repo.
- Does not copy credentials, MFA codes, browser cookies, account recovery data, or private keys.
- Does not grant this hosted session browser control by itself.
- Final legal grant certification and submission remain human-operated.

## Summary

| Metric | Count |
|---|---:|
| Total matched plugin/MCP files | $($Summary.total_matches) |
| Browser/computer-control candidates | $($Summary.browser_or_computer_control_candidates) |
| MCP/bridge candidates | $($Summary.mcp_or_bridge_candidates) |
| Grant-submission candidates | $($Summary.grant_submission_candidates) |

## Browser / Computer-Control Candidates

$($TopBrowser | ForEach-Object { "- ``$($_.path)``" } | Out-String)

## MCP / Bridge Candidates

$($TopMcp | ForEach-Object { "- ``$($_.path)``" } | Out-String)

## Grant Submission Candidates

$($TopGrant | ForEach-Object { "- ``$($_.path)``" } | Out-String)

## How to Use This Packet

1. Run this script from the LumenCore repo root on the Windows machine that has the Codex plugins.
2. Open ``data/local_codex_plugin_session_manifest.json`` and this markdown packet in the next Codex session.
3. In the Codex launcher or settings, enable the Playwright/browser-control MCP server shown by the local plugin paths.
4. Restart the Codex session with that MCP server attached.
5. Keep credentials and MFA inside the browser only; do not paste them into chat.

## Generated Files

- ``data/local_codex_plugin_session_manifest.json``
- ``docs/LOCAL_CODEX_PLUGIN_SESSION_PACKET.md``
"@

$Markdown | Set-Content -Path $MdPath -Encoding UTF8

Write-Host ""
Write-Host "Wrote session packet:" -ForegroundColor Green
Write-Host "  $JsonPath"
Write-Host "  $MdPath"
Write-Host ""
Write-Host "Next: commit these generated non-secret files if you want future sessions to see the plugin map." -ForegroundColor Cyan
