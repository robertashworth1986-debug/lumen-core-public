param(
  [string]$LeadCsvPath = "",
  [string]$OutputDir = "",
  [datetime]$EventDate = [datetime]"2026-05-21T18:00:00",
  [string]$SlotsCsvPath = "",
  [int]$SlotsPerLead = 2,
  [switch]$OpenOutput
)

$ErrorActionPreference = "Stop"

function Get-WorkspaceRoot {
  return (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
}

function Clean-Text {
  param([object]$Value)
  if ($null -eq $Value) { return "" }
  return ([string]$Value).Trim()
}

function Get-CsvHeaderColumns {
  param([string]$Path)

  $headerLine = Get-Content -Path $Path -TotalCount 1
  if ([string]::IsNullOrWhiteSpace($headerLine)) {
    return @()
  }

  $headers = @()
  foreach ($raw in ($headerLine -split ',')) {
    $headers += (Clean-Text $raw).Trim('"')
  }
  return $headers
}

function Try-ParseDate {
  param([string]$Value)

  if ([string]::IsNullOrWhiteSpace($Value)) {
    return $null
  }

  $parsed = [datetime]::MinValue
  if ([datetime]::TryParse($Value, [ref]$parsed)) {
    return $parsed
  }

  return $null
}

function Get-Priority {
  param([string]$Fit)

  switch ((Clean-Text $Fit).ToUpperInvariant()) {
    "A" { return "P1" }
    "B" { return "P2" }
    "C" { return "P3" }
    default { return "P2" }
  }
}

function Get-DefaultDueDate {
  param(
    [string]$Fit,
    [datetime]$EventClose
  )

  switch ((Clean-Text $Fit).ToUpperInvariant()) {
    "A" { return $EventClose.AddHours(2) }
    "B" { return $EventClose.AddDays(1).Date.AddHours(10) }
    "C" { return $EventClose.AddDays(3).Date.AddHours(10) }
    default { return $EventClose.AddDays(2).Date.AddHours(10) }
  }
}

function Get-TemplateName {
  param([string]$LeadType)

  switch ((Clean-Text $LeadType).ToLowerInvariant()) {
    "investor" { return "Investor follow-up" }
    "partner" { return "Partner follow-up" }
    "customer" { return "Customer/operator follow-up" }
    "operator" { return "Customer/operator follow-up" }
    default { return "Same-day short follow-up" }
  }
}

function Get-SubjectLine {
  param([string]$LeadType)

  switch ((Clean-Text $LeadType).ToLowerInvariant()) {
    "investor" { return "LumenCore follow-up and next-step diligence" }
    "partner" { return "Potential partnership follow-up" }
    "customer" { return "Follow-up on your workflow use case" }
    "operator" { return "Follow-up on your workflow use case" }
    default { return "Great meeting you at Nashville Entrepreneur Day" }
  }
}

function Get-DefaultMeetingSlots {
  param([datetime]$EventClose)

  $firstDay = $EventClose.Date.AddDays(1)
  while ($firstDay.DayOfWeek -ne [System.DayOfWeek]::Monday) {
    $firstDay = $firstDay.AddDays(1)
  }

  return @(
    [pscustomobject]@{ slot_local = $firstDay.AddHours(10).ToString("yyyy-MM-dd HH:mm"); label = "Mon 10:00 AM" }
    [pscustomobject]@{ slot_local = $firstDay.AddHours(14).ToString("yyyy-MM-dd HH:mm"); label = "Mon 2:00 PM" }
    [pscustomobject]@{ slot_local = $firstDay.AddDays(1).AddHours(10).ToString("yyyy-MM-dd HH:mm"); label = "Tue 10:00 AM" }
    [pscustomobject]@{ slot_local = $firstDay.AddDays(1).AddHours(14).ToString("yyyy-MM-dd HH:mm"); label = "Tue 2:00 PM" }
    [pscustomobject]@{ slot_local = $firstDay.AddDays(2).AddHours(11).ToString("yyyy-MM-dd HH:mm"); label = "Wed 11:00 AM" }
    [pscustomobject]@{ slot_local = $firstDay.AddDays(3).AddHours(13).ToString("yyyy-MM-dd HH:mm"); label = "Thu 1:00 PM" }
  )
}

function Load-MeetingSlots {
  param(
    [string]$Path,
    [datetime]$EventClose
  )

  if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path $Path)) {
    return Get-DefaultMeetingSlots -EventClose $EventClose
  }

  $slotRows = Import-Csv -Path $Path
  $slots = New-Object System.Collections.Generic.List[object]
  foreach ($row in $slotRows) {
    $slotValue = Clean-Text $row.slot_local
    if ([string]::IsNullOrWhiteSpace($slotValue)) {
      continue
    }

    $parsed = Try-ParseDate -Value $slotValue
    if (-not $parsed) {
      continue
    }

    $label = Clean-Text $row.label
    if ([string]::IsNullOrWhiteSpace($label)) {
      $label = $parsed.ToString("ddd h:mm tt")
    }

    $slots.Add([pscustomobject]@{
      slot_local = $parsed.ToString("yyyy-MM-dd HH:mm")
      label = $label
    })
  }

  if ($slots.Count -eq 0) {
    return Get-DefaultMeetingSlots -EventClose $EventClose
  }

  return @(
    $slots | Sort-Object slot_local -Unique
  )
}

function Get-SlotDisplay {
  param([pscustomobject]$Slot)

  if ($null -eq $Slot) {
    return ""
  }

  if ([string]::IsNullOrWhiteSpace($Slot.label)) {
    return [string]$Slot.slot_local
  }

  return "$($Slot.label) ($($Slot.slot_local))"
}

function Get-SlotOptionsForLead {
  param(
    [object[]]$Slots,
    [int]$LeadIndex,
    [int]$PerLead
  )

  if ($null -eq $Slots -or $Slots.Count -eq 0) {
    return @()
  }

  if ($PerLead -lt 1) {
    $PerLead = 1
  }

  $takeCount = [Math]::Min($PerLead, $Slots.Count)
  $stride = [Math]::Max($takeCount, 1)
  $start = ($LeadIndex * $stride) % $Slots.Count

  $picked = New-Object System.Collections.Generic.List[string]
  for ($i = 0; $i -lt $takeCount; $i++) {
    $slot = $Slots[($start + $i) % $Slots.Count]
    $picked.Add((Get-SlotDisplay -Slot $slot))
  }

  return @($picked)
}

function Build-SlotPrompt {
  param([string[]]$SlotOptions)

  if ($null -eq $SlotOptions -or $SlotOptions.Count -eq 0) {
    return "Would you be open to a 20-minute call next week?"
  }

  if ($SlotOptions.Count -eq 1) {
    return "Would $($SlotOptions[0]) work for a 20-minute call?"
  }

  return "Would $($SlotOptions[0]) or $($SlotOptions[1]) work for a 20-minute call?"
}

function Get-NonEmptyStrings {
  param([string[]]$Values)

  return @(
    $Values | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
  )
}

function Build-Draft {
  param(
    [pscustomobject]$Lead,
    [pscustomobject]$Task
  )

  $firstName = if ([string]::IsNullOrWhiteSpace($Lead.name)) { "there" } else { (($Lead.name -split "\\s+")[0]).Trim() }
  $painPoint = if ([string]::IsNullOrWhiteSpace($Lead.pain_point)) { "your current workflow" } else { $Lead.pain_point }
  $slotOptions = Get-NonEmptyStrings -Values @($Task.slot_option_1, $Task.slot_option_2)
  $slotPrompt = Build-SlotPrompt -SlotOptions $slotOptions

  switch ($Task.recommended_template) {
    "Investor follow-up" {
      return @(
        "Hi $firstName,",
        "",
        "Thank you for the conversation at Nashville Entrepreneur Day.",
        "I appreciated your perspective around investment readiness and next-step diligence.",
        "",
        "If useful, I can run a focused 20-minute walkthrough covering architecture, live endpoints, and go-to-market priorities.",
        $slotPrompt,
        "",
        "Best,",
        "Robert"
      ) -join [Environment]::NewLine
    }
    "Partner follow-up" {
      return @(
        "Hi $firstName,",
        "",
        "Great meeting you at Nashville Entrepreneur Day.",
        "I see strong overlap between your work and our live decision stack.",
        "",
        "Would you be open to a short partnership scoping call to align use case, integration boundary, and pilot success criteria?",
        $slotPrompt,
        "",
        "Best,",
        "Robert"
      ) -join [Environment]::NewLine
    }
    "Customer/operator follow-up" {
      return @(
        "Hi $firstName,",
        "",
        "Great connecting at Nashville Entrepreneur Day.",
        "You mentioned $painPoint, and I think a focused fit session would quickly show whether this can help your team.",
        "",
        $slotPrompt,
        "",
        "Best,",
        "Robert"
      ) -join [Environment]::NewLine
    }
    default {
      return @(
        "Hi $firstName,",
        "",
        "Great meeting you today at Nashville Entrepreneur Day.",
        "As promised, here is the platform link: https://lumen-core.ai/mission_control.html",
        "",
        $slotPrompt,
        "",
        "Best,",
        "Robert"
      ) -join [Environment]::NewLine
    }
  }
}

function Build-SmsDraft {
  param(
    [pscustomobject]$Lead,
    [pscustomobject]$Task
  )

  $firstName = if ([string]::IsNullOrWhiteSpace($Lead.name)) { "there" } else { (($Lead.name -split "\\s+")[0]).Trim() }
  $slotOptions = Get-NonEmptyStrings -Values @($Task.slot_option_1, $Task.slot_option_2)
  $slotPrompt = Build-SlotPrompt -SlotOptions $slotOptions

  return "Hi $firstName - Robert from Nashville Entrepreneur Day. $slotPrompt"
}

function Build-LinkedInDraft {
  param(
    [pscustomobject]$Lead,
    [pscustomobject]$Task
  )

  $firstName = if ([string]::IsNullOrWhiteSpace($Lead.name)) { "there" } else { (($Lead.name -split "\\s+")[0]).Trim() }
  $slotOptions = Get-NonEmptyStrings -Values @($Task.slot_option_1, $Task.slot_option_2)
  $slotPrompt = Build-SlotPrompt -SlotOptions $slotOptions

  return "Great meeting you at Nashville Entrepreneur Day, $firstName. $slotPrompt"
}

function Export-CsvWithHeaders {
  param(
    [string]$Path,
    [string[]]$Headers,
    [System.Collections.IEnumerable]$Rows
  )

  $rowBuffer = New-Object System.Collections.Generic.List[object]
  if ($null -ne $Rows) {
    foreach ($row in $Rows) {
      $rowBuffer.Add($row)
    }
  }

  if ($rowBuffer.Count -gt 0) {
    $rowBuffer | Export-Csv -Path $Path -NoTypeInformation -Encoding UTF8
    return
  }

  $headerLine = '"' + ($Headers -join '","') + '"'
  Set-Content -Path $Path -Value $headerLine -Encoding UTF8
}

$workspaceRoot = Get-WorkspaceRoot
$reportsRoot = Join-Path $workspaceRoot "reports\NED_Showcase_2026-05-21"

if ([string]::IsNullOrWhiteSpace($LeadCsvPath)) {
  $LeadCsvPath = Join-Path $reportsRoot "LEAD_CAPTURE_TEMPLATE.csv"
}

if ([string]::IsNullOrWhiteSpace($SlotsCsvPath)) {
  $SlotsCsvPath = Join-Path $reportsRoot "MEETING_SLOTS_TEMPLATE.csv"
}

if (-not (Test-Path $LeadCsvPath)) {
  throw "Lead CSV not found: $LeadCsvPath"
}

$meetingSlots = Load-MeetingSlots -Path $SlotsCsvPath -EventClose $EventDate

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
  $stamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
  $OutputDir = Join-Path $reportsRoot ("automation_out\" + $stamp)
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$actualLeadColumns = Get-CsvHeaderColumns -Path $LeadCsvPath
$actualLeadColumnsLookup = @{}
foreach ($name in $actualLeadColumns) {
  if (-not $actualLeadColumnsLookup.ContainsKey($name)) {
    $actualLeadColumnsLookup[$name] = $true
  }
}

$rows = Import-Csv -Path $LeadCsvPath
$requiredColumns = @(
  "captured_utc",
  "name",
  "company",
  "title",
  "email",
  "phone",
  "linkedin",
  "lead_type",
  "fit_score_A_B_C",
  "pain_point",
  "current_solution",
  "urgency",
  "decision_authority",
  "next_step",
  "next_step_date",
  "notes"
)

$missingColumns = @()
foreach ($col in $requiredColumns) {
  if (-not $actualLeadColumnsLookup.ContainsKey($col)) {
    $missingColumns += $col
  }
}

if ($missingColumns.Count -gt 0) {
  throw "Lead CSV is missing required columns: $($missingColumns -join ', ')"
}

$priorityOrder = @{ "P1" = 1; "P2" = 2; "P3" = 3 }
$tasks = New-Object System.Collections.Generic.List[object]
$normalizedLeads = New-Object System.Collections.Generic.List[object]

foreach ($row in $rows) {
  $lead = [pscustomobject]@{
    captured_utc = Clean-Text $row.captured_utc
    name = Clean-Text $row.name
    company = Clean-Text $row.company
    title = Clean-Text $row.title
    email = Clean-Text $row.email
    phone = Clean-Text $row.phone
    linkedin = Clean-Text $row.linkedin
    lead_type = if ([string]::IsNullOrWhiteSpace((Clean-Text $row.lead_type))) { "customer" } else { (Clean-Text $row.lead_type).ToLowerInvariant() }
    fit_score_A_B_C = if ([string]::IsNullOrWhiteSpace((Clean-Text $row.fit_score_A_B_C))) { "B" } else { (Clean-Text $row.fit_score_A_B_C).ToUpperInvariant() }
    pain_point = Clean-Text $row.pain_point
    current_solution = Clean-Text $row.current_solution
    urgency = Clean-Text $row.urgency
    decision_authority = Clean-Text $row.decision_authority
    next_step = Clean-Text $row.next_step
    next_step_date = Clean-Text $row.next_step_date
    notes = Clean-Text $row.notes
  }

  $hasSignal = @(
    $lead.name,
    $lead.company,
    $lead.email,
    $lead.phone,
    $lead.linkedin,
    $lead.pain_point,
    $lead.next_step,
    $lead.notes
  ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

  if ($hasSignal.Count -eq 0) {
    continue
  }

  $slotOptions = Get-SlotOptionsForLead -Slots $meetingSlots -LeadIndex $tasks.Count -PerLead $SlotsPerLead

  $parsedNextStep = Try-ParseDate -Value $lead.next_step_date
  $dueDate = if ($parsedNextStep) { $parsedNextStep } else { Get-DefaultDueDate -Fit $lead.fit_score_A_B_C -EventClose $EventDate }

  $task = [pscustomobject]@{
    task_id = "NED-" + (($tasks.Count + 1).ToString("000"))
    priority = Get-Priority -Fit $lead.fit_score_A_B_C
    due_local = $dueDate.ToString("yyyy-MM-dd HH:mm")
    name = $lead.name
    company = $lead.company
    title = $lead.title
    email = $lead.email
    phone = $lead.phone
    lead_type = $lead.lead_type
    fit_score = $lead.fit_score_A_B_C
    pain_point = $lead.pain_point
    urgency = $lead.urgency
    decision_authority = $lead.decision_authority
    next_step = $lead.next_step
    next_step_date = $lead.next_step_date
    recommended_template = Get-TemplateName -LeadType $lead.lead_type
    recommended_subject = Get-SubjectLine -LeadType $lead.lead_type
    slot_option_1 = if ($slotOptions.Count -ge 1) { $slotOptions[0] } else { "" }
    slot_option_2 = if ($slotOptions.Count -ge 2) { $slotOptions[1] } else { "" }
    slot_prompt = Build-SlotPrompt -SlotOptions $slotOptions
    status = "todo"
    notes = $lead.notes
  }

  $normalizedLeads.Add($lead)
  $tasks.Add($task)
}

$sortedTasks = @(
  $tasks | Sort-Object @{ Expression = { $priorityOrder[[string]$_.priority] } }, @{ Expression = { [datetime]$_.due_local } }
)

$summaryPath = Join-Path $OutputDir "lead_summary.json"
$tasksPath = Join-Path $OutputDir "followup_tasks.csv"
$draftsPath = Join-Path $OutputDir "outreach_drafts.md"
$multiPath = Join-Path $OutputDir "outreach_multichannel.csv"
$smsPath = Join-Path $OutputDir "sms_drafts.csv"
$linkedinPath = Join-Path $OutputDir "linkedin_drafts.csv"
$priorityBoardPath = Join-Path $OutputDir "priority_board.md"

$withEmailCount = @($sortedTasks | Where-Object { -not [string]::IsNullOrWhiteSpace($_.email) }).Count
$withPhoneCount = @($sortedTasks | Where-Object { -not [string]::IsNullOrWhiteSpace($_.phone) }).Count
$withLinkedInCount = @($sortedTasks | Where-Object { -not [string]::IsNullOrWhiteSpace($_.linkedin) }).Count
$meetingIntentCount = @($sortedTasks | Where-Object {
  -not [string]::IsNullOrWhiteSpace($_.next_step_date) -or $_.next_step -match "call|meeting|demo|intro"
}).Count
$readyNowCount = @($sortedTasks | Where-Object { $_.priority -eq "P1" }).Count

$byType = @(
  $sortedTasks | Group-Object lead_type | Sort-Object Name | ForEach-Object {
    [pscustomobject]@{ lead_type = $_.Name; count = $_.Count }
  }
)

$byFit = @(
  $sortedTasks | Group-Object fit_score | Sort-Object Name | ForEach-Object {
    [pscustomobject]@{ fit_score = $_.Name; count = $_.Count }
  }
)

$summary = [pscustomobject]@{
  generated_utc = (Get-Date).ToUniversalTime().ToString("o")
  source_csv = (Resolve-Path $LeadCsvPath).Path
  output_dir = (Resolve-Path $OutputDir).Path
  total_leads = $sortedTasks.Count
  with_email = $withEmailCount
  with_phone = $withPhoneCount
  with_linkedin = $withLinkedInCount
  p1_ready_now = $readyNowCount
  meeting_intent_detected = $meetingIntentCount
  slots_loaded = $meetingSlots.Count
  slots_source = if (Test-Path $SlotsCsvPath) { (Resolve-Path $SlotsCsvPath).Path } else { "default_generated" }
  breakdown_by_type = $byType
  breakdown_by_fit = $byFit
}

$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $summaryPath -Encoding UTF8

$taskHeaders = @(
  "task_id",
  "priority",
  "due_local",
  "name",
  "company",
  "title",
  "email",
  "phone",
  "lead_type",
  "fit_score",
  "pain_point",
  "urgency",
  "decision_authority",
  "next_step",
  "next_step_date",
  "recommended_template",
  "recommended_subject",
  "slot_option_1",
  "slot_option_2",
  "slot_prompt",
  "status",
  "notes"
)
$smsHeaders = @("task_id", "priority", "name", "company", "phone", "email", "due_local", "sms_draft")
$linkedinHeaders = @("task_id", "priority", "name", "company", "linkedin", "email", "due_local", "linkedin_draft")
$multiHeaders = @(
  "task_id",
  "priority",
  "due_local",
  "name",
  "company",
  "lead_type",
  "recommended_template",
  "email_subject",
  "email_draft",
  "sms_draft",
  "linkedin_draft",
  "slot_option_1",
  "slot_option_2",
  "status"
)

Export-CsvWithHeaders -Path $tasksPath -Headers $taskHeaders -Rows $sortedTasks

$smsRows = New-Object System.Collections.Generic.List[object]
$linkedinRows = New-Object System.Collections.Generic.List[object]
$multiRows = New-Object System.Collections.Generic.List[object]

$draftLines = New-Object System.Collections.Generic.List[string]
$draftLines.Add("# Outreach Drafts")
$draftLines.Add("")
$draftLines.Add("Generated: $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))")
$draftLines.Add("Source: $LeadCsvPath")
$draftLines.Add("")

if ($sortedTasks.Count -eq 0) {
  $draftLines.Add("No actionable leads found yet. Add real lead rows to the capture CSV, then rerun this script.")
}
else {
  foreach ($task in $sortedTasks) {
    $lead = $normalizedLeads | Where-Object {
      $_.name -eq $task.name -and $_.company -eq $task.company -and $_.email -eq $task.email
    } | Select-Object -First 1

    if (-not $lead) {
      $lead = [pscustomobject]@{ name = $task.name; pain_point = $task.pain_point; phone = $task.phone; linkedin = "" }
    }

    $emailDraft = Build-Draft -Lead $lead -Task $task
    $smsDraft = Build-SmsDraft -Lead $lead -Task $task
    $linkedinDraft = Build-LinkedInDraft -Lead $lead -Task $task

    $smsRows.Add([pscustomobject]@{
      task_id = $task.task_id
      priority = $task.priority
      name = $task.name
      company = $task.company
      phone = $task.phone
      email = $task.email
      due_local = $task.due_local
      sms_draft = $smsDraft
    })

    $linkedinRows.Add([pscustomobject]@{
      task_id = $task.task_id
      priority = $task.priority
      name = $task.name
      company = $task.company
      linkedin = $task.linkedin
      email = $task.email
      due_local = $task.due_local
      linkedin_draft = $linkedinDraft
    })

    $multiRows.Add([pscustomobject]@{
      task_id = $task.task_id
      priority = $task.priority
      due_local = $task.due_local
      name = $task.name
      company = $task.company
      lead_type = $task.lead_type
      recommended_template = $task.recommended_template
      email_subject = $task.recommended_subject
      email_draft = $emailDraft
      sms_draft = $smsDraft
      linkedin_draft = $linkedinDraft
      slot_option_1 = $task.slot_option_1
      slot_option_2 = $task.slot_option_2
      status = $task.status
    })

    $draftLines.Add("## $($task.task_id) - $($task.name)")
    $draftLines.Add("")
    $draftLines.Add("- Priority: $($task.priority)")
    $draftLines.Add("- Due: $($task.due_local)")
    $draftLines.Add("- Lead type: $($task.lead_type)")
    $draftLines.Add("- Subject: $($task.recommended_subject)")
    $draftLines.Add("- Slot option 1: $($task.slot_option_1)")
    $draftLines.Add("- Slot option 2: $($task.slot_option_2)")
    $draftLines.Add("")
    $draftLines.Add($emailDraft)
    $draftLines.Add("")
    $draftLines.Add("SMS draft:")
    $draftLines.Add($smsDraft)
    $draftLines.Add("")
    $draftLines.Add("LinkedIn draft:")
    $draftLines.Add($linkedinDraft)
    $draftLines.Add("")
    $draftLines.Add("---")
    $draftLines.Add("")
  }
}

$draftLines | Set-Content -Path $draftsPath -Encoding UTF8
Export-CsvWithHeaders -Path $smsPath -Headers $smsHeaders -Rows $smsRows
Export-CsvWithHeaders -Path $linkedinPath -Headers $linkedinHeaders -Rows $linkedinRows
Export-CsvWithHeaders -Path $multiPath -Headers $multiHeaders -Rows $multiRows

$boardLines = New-Object System.Collections.Generic.List[string]
$boardLines.Add("# Priority Board")
$boardLines.Add("")
$boardLines.Add("Generated: $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))")
$boardLines.Add("")

if ($sortedTasks.Count -eq 0) {
  $boardLines.Add("No prioritized tasks yet.")
}
else {
  foreach ($task in $sortedTasks) {
    $label = if ([string]::IsNullOrWhiteSpace($task.name)) { "Unknown contact" } else { $task.name }
    $org = if ([string]::IsNullOrWhiteSpace($task.company)) { "Unknown org" } else { $task.company }
    $boardLines.Add("- $($task.task_id) | $($task.priority) | $($task.due_local) | $label | $org | $($task.recommended_template)")
  }
}

$boardLines | Set-Content -Path $priorityBoardPath -Encoding UTF8

Write-Host ""
Write-Host "NED lead pipeline automation complete"
Write-Host "- leads processed: $($summary.total_leads)"
Write-Host "- p1 ready now:   $($summary.p1_ready_now)"
Write-Host "- slots loaded:   $($summary.slots_loaded)"
Write-Host "- output dir:     $OutputDir"
Write-Host ""
Write-Host "Artifacts"
Write-Host "- $summaryPath"
Write-Host "- $tasksPath"
Write-Host "- $draftsPath"
Write-Host "- $multiPath"
Write-Host "- $smsPath"
Write-Host "- $linkedinPath"
Write-Host "- $priorityBoardPath"

if ($OpenOutput) {
  Invoke-Item -Path $OutputDir
}
