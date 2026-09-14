"""Stub unsafe legacy decisions; exercise native control only on owned fixtures."""
from pathlib import Path
import os
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MANAGER = ROOT / "code/ops/STACK_RUNTIME_MANAGER.ps1"
POWERSHELL = shutil.which("powershell.exe")
pytestmark = pytest.mark.skipif(os.name != "nt" or not POWERSHELL, reason="Windows runtime manager")


def ps_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def run_functions(tmp_path, body):
    fixture = tmp_path / "fixture stack"
    fixture.mkdir()
    script = tmp_path / "check.ps1"
    script.write_text("\n".join([
        "$ErrorActionPreference='Stop'", "$ProgressPreference='SilentlyContinue'",
        f"$stackRoot={ps_literal(fixture)}", "$codeRoot=Join-Path $stackRoot 'code'",
        f"$identitySource={ps_literal(ROOT / 'code/ops/RUNTIME_PROCESS_IDENTITY.cs')}",
        "$runRoot=Join-Path $stackRoot 'run'", "$registryPath=Join-Path $runRoot 'managed_runtime_processes.json'",
        "$tokens=$null; $errors=$null",
        f"$tree=[System.Management.Automation.Language.Parser]::ParseFile({ps_literal(MANAGER)},[ref]$tokens,[ref]$errors)",
        "if($errors.Count){throw ($errors|Out-String)}",
        "foreach($statement in $tree.EndBlock.Statements){if($statement -is [System.Management.Automation.Language.FunctionDefinitionAst]){Invoke-Expression $statement.Extent.Text}}",
        "$script:stopped=@()",
        "function Stop-Process { param([int]$Id,[switch]$Force,[string]$ErrorAction,[object]$InputObject) $script:stopped+= $Id }",
        "function Assert-That { param([bool]$Condition,[string]$Message) if(-not $Condition){throw $Message} }",
        body,
    ]), encoding="utf-8")
    result = subprocess.run([POWERSHELL, "-NoProfile", "-NonInteractive", "-File", str(script)],
                            cwd=fixture, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


def test_substring_matches_cannot_authorize_process_termination(tmp_path):
    run_functions(tmp_path, r"""
function Find-PythonProcessByNeedle { param([string]$Needle) @([pscustomobject]@{ProcessId=303;CommandLine='python.exe C:\unrelated\execution_orchestrator.py'}) }
try { Stop-PythonProcessesByNeedle -Needle 'execution_orchestrator.py' -ServiceName 'orchestrator' } catch { }
Assert-That ($script:stopped.Count -eq 0) 'A substring match terminated an unrelated process'
""")


def test_legacy_pid_record_does_not_authorize_stop(tmp_path):
    run_functions(tmp_path, r"""
function Test-ProcessAlive { param([int]$ProcessNumber) $true }
$record=[pscustomobject]@{name='gateway';process_number=303;started_utc='2026-01-01T00:00:00Z'}
try { Stop-ServiceRecord -Record $record -ForceStop } catch { }
Assert-That ($script:stopped.Count -eq 0) 'A legacy PID-only record authorized stop'
""")


def test_force_start_does_not_take_over_an_unrelated_port_listener(tmp_path):
    run_functions(tmp_path, r"""
function Get-NetTCPConnection { param($LocalPort,$State,$ErrorAction) [pscustomobject]@{OwningProcess=303;LocalPort=8787} }
function Get-PythonProcessInventory { @() }
function Find-PythonProcessByNeedle { param($Needle) @() }
function Start-Process { param($FilePath,$ArgumentList,$WorkingDirectory,$PassThru,$WindowStyle,$Environment) throw 'Fixture forbids a real launch' }
$service=[pscustomobject]@{Name='gateway';WorkDir=$codeRoot;Arguments=@('-m','uvicorn','luma_experience_gateway:app');MatchNeedle='uvicorn luma_experience_gateway:app'}
$reason=''
try { Start-ServiceFromPlan -Service $service -Records @() -PythonRuntime 'C:\fixture\python.exe' -PythonPath $codeRoot -GroupName 'dashboard' -ForceStart } catch { $reason=$_.Exception.Message }
Assert-That ($script:stopped.Count -eq 0) 'Force start killed an unrelated port listener'
Assert-That ($reason -like '*occupied*') 'The occupied-port hold was not reached'
""")


def test_malformed_registry_is_a_hold_not_an_empty_registry(tmp_path):
    run_functions(tmp_path, r"""
New-Item -ItemType Directory -Path $runRoot | Out-Null
[IO.File]::WriteAllText($registryPath,'{broken')
$held=$false
try { $null=Read-Registry } catch { $held=$true }
Assert-That $held 'Malformed registry was treated as empty'
Assert-That ([IO.File]::ReadAllText($registryPath) -eq '{broken') 'Malformed registry was overwritten'
""")


def test_status_does_not_create_runtime_state_or_require_a_python_environment(tmp_path):
    fixture = tmp_path / "empty stack"
    target = fixture / "code/ops/STACK_RUNTIME_MANAGER.ps1"
    target.parent.mkdir(parents=True)
    target.write_bytes(MANAGER.read_bytes())
    result = subprocess.run([POWERSHELL, "-NoProfile", "-NonInteractive", "-File", str(target),
                             "-Action", "status"], cwd=fixture, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (fixture / "run").exists(), "A read-only status invocation created runtime state"


@pytest.mark.parametrize("interpreter", ["base", "venv"])
def test_native_launch_records_exact_identity_and_only_stops_its_fixture(tmp_path, interpreter):
    runtime = sys._base_executable if interpreter == "base" else sys.executable
    run_functions(tmp_path, r"""
New-Item -ItemType Directory -Path $codeRoot,$runRoot | Out-Null
$fixturePath=Join-Path $codeRoot 'owned_manager_fixture.py'
$resultPath=Join-Path $codeRoot 'owned_manager_fixture.json'
$stopPath=Join-Path $codeRoot 'owned_manager_fixture.stop'
$body=@'
import json,os,sys,time
from pathlib import Path
path=Path(__file__)
path.with_suffix('.json').write_text(json.dumps({'pid':os.getpid(),'args':sys.argv[1:],'pythonpath':os.environ.get('PYTHONPATH')}))
while not path.with_suffix('.stop').exists(): time.sleep(.05)
'@
[IO.File]::WriteAllText($fixturePath,$body)
$script:ownedService=[pscustomobject]@{Name='fixture';WorkDir=$codeRoot;Arguments=@($fixturePath,'argument with spaces','a"quote','trailing\','');MatchNeedle='owned_manager_fixture.py'}
function Get-ServicePlan { param($GroupName) @($script:ownedService) }
# Native process checks are restricted to this disposable fixture. Unreadable
# unrelated system workers are exercised separately as a production HOLD.
function Get-PythonProcessInventory {
    @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -OperationTimeoutSec 5 -ErrorAction Stop |
      Where-Object { $_.CommandLine -and $_.CommandLine.Contains($fixturePath) })
}
$records=@()
try {
    $records=@(Start-ServiceFromPlan $script:ownedService @() RUNTIME_PLACEHOLDER $codeRoot 'fixture')
    Assert-That ($records.Count -eq 1) 'Native launch did not return one record'
    $record=$records[0]
    Assert-That ($record.ownership -eq 'launched_by_manager') 'Ownership not recorded'
    Assert-That ($record.application_health_verified -eq $false) 'Process presence promoted to application health'
    $timer=[Diagnostics.Stopwatch]::StartNew()
    while (-not (Test-Path -LiteralPath $resultPath) -and $timer.Elapsed.TotalSeconds -lt 10) { Start-Sleep -Milliseconds 100 }
    $result=Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
    Assert-That ($result.args.Count -eq 4 -and $result.args[0] -eq 'argument with spaces' -and $result.args[1] -eq 'a"quote' -and $result.args[2] -eq 'trailing\' -and $result.args[3] -eq '') 'Native argument vector was not preserved'
    Assert-That ($result.pythonpath -eq $codeRoot) 'Per-child Python environment was not preserved'
    Assert-That (@($record.members | Where-Object { $_.process_number -eq $result.pid }).Count -eq 1) 'Actual Python child missing from registry'
    Assert-That ((Get-RecordObservation $record) -eq 'REGISTERED_PROCESSES_PRESENT') 'Registered identity could not be observed'
    $member=$record.members[-1]
    $originalCreation=$member.creation_filetime
    $member.creation_filetime=([UInt64]$originalCreation+1).ToString()
    $held=$false
    try { Stop-ServiceRecord $record -ForceStop } catch { $held=$true }
    Assert-That $held 'Changed creation identity did not hold stop'
    $member.creation_filetime=$originalCreation
    foreach($entry in $record.members){$lease=Get-ProcessLeaseOrAbsent $entry.process_number;try{Assert-That $lease.Alive 'Identity-mismatch check stopped a member'}finally{$lease.Dispose()}}
    $proofLeases=@($record.members | ForEach-Object { Get-ProcessLeaseOrAbsent $_.process_number })
    try {
        Stop-ServiceRecord $record -ForceStop
        foreach($lease in $proofLeases){Assert-That (-not $lease.Alive) 'Registered child did not exit'}
    } finally { foreach($lease in $proofLeases){$lease.Dispose()} }
} finally {
    [IO.File]::WriteAllText($stopPath,'stop')
    foreach($record in $records){try{Stop-ServiceRecord $record -ForceStop}catch{}}
}
""".replace("RUNTIME_PLACEHOLDER", ps_literal(runtime)))


@pytest.mark.parametrize("payload", ["null", "{}", "[null]", '1,"records":[]', '[{"name":"x","pid":1},null]', '[{"name":"x","pid":0}]',
                                     '[{"name":"x","pid":1},{"name":"x","pid":2}]'])
def test_invalid_registry_shape_is_preserved_and_blocks_control(tmp_path, payload):
    run_functions(tmp_path, "\n".join([
        "New-Item -ItemType Directory -Path $runRoot | Out-Null",
        f"[IO.File]::WriteAllText($registryPath,{ps_literal(payload)})",
        "$held=$false;try{$null=Read-Registry}catch{$held=$true}",
        "Assert-That $held 'Invalid registry was accepted'",
        f"Assert-That ([IO.File]::ReadAllText($registryPath) -eq {ps_literal(payload)}) 'Invalid registry changed'",
    ]))


def test_atomic_registry_round_trip_preserves_arrays_and_empty_state(tmp_path):
    run_functions(tmp_path, r"""
New-Item -ItemType Directory -Path $runRoot | Out-Null
Write-Registry @()
Assert-That (@(Read-Registry).Count -eq 0) 'Empty array did not round trip'
Write-Registry @([pscustomobject]@{name='fixture';process_number=42;argument_vector=@('one','two')})
$roundtrip=@(Read-Registry)
Assert-That ($roundtrip.Count -eq 1 -and $roundtrip[0].argument_vector.Count -eq 2) 'Registry shape changed'
Write-Registry @()
Assert-That ([IO.File]::ReadAllText($registryPath) -match '^\s*\[\s*\]\s*$') 'Final empty registry is not valid JSON'
Assert-That (@(Get-ChildItem -LiteralPath $runRoot -Filter '*.tmp').Count -eq 0) 'Atomic write left temporary files'
""")


def test_unreadable_process_inventory_blocks_launch(tmp_path):
    run_functions(tmp_path, r"""
function Get-PythonProcessInventory { @([pscustomobject]@{ProcessId=303;CommandLine=$null;ExecutablePath=$null}) }
$service=[pscustomobject]@{Name='fixture';WorkDir=$codeRoot;Arguments=@('fixture.py');MatchNeedle='fixture.py'}
$reason=''
try { Start-ServiceFromPlan $service @() 'C:\fixture\python.exe' $codeRoot 'fixture' } catch { $reason=$_.Exception.Message }
Assert-That ($reason -like '*unreadable*') 'Unreadable process inventory did not HOLD launch'
Assert-That (-not (Test-Path -LiteralPath $runRoot)) 'Held launch wrote runtime state'
""")


@pytest.mark.parametrize("capture", ["$false", "'true'", "$null"])
def test_incomplete_capture_cannot_authorize_reuse_or_stop(tmp_path, capture):
    run_functions(tmp_path, r"""
$record=[pscustomobject]@{schema='lumencore.managed_runtime_process.v2';ownership='launched_by_manager';capture_complete=CAPTURE_PLACEHOLDER;name='fixture';process_number=303;members=@()}
$service=[pscustomobject]@{Name='fixture';WorkDir=$codeRoot;Arguments=@('fixture.py');MatchNeedle='fixture.py'}
Assert-That ((Get-RecordObservation $record) -eq 'CAPTURE_INCOMPLETE') 'Incomplete capture was promoted to presence'
$stopReason='';$startReason=''
try { Stop-ServiceRecord $record -ForceStop } catch { $stopReason=$_.Exception.Message }
try { Start-ServiceFromPlan $service @($record) 'C:\fixture\python.exe' $codeRoot 'fixture' -ForceStart } catch { $startReason=$_.Exception.Message }
Assert-That ($stopReason -like '*Incomplete*' -and $startReason -like '*CAPTURE_INCOMPLETE*') 'Incomplete record did not hold both stop and force-start'
""".replace("CAPTURE_PLACEHOLDER", capture))


def test_exclusive_manager_lock_prevents_any_service_action(tmp_path):
    run_functions(tmp_path, r"""
New-Item -ItemType Directory -Path $runRoot | Out-Null
$Action='start';$StackGroup='core';$Force=$true;$Json=$false
$script:servicePlanCalled=$false
function Get-ServicePlan {param($GroupName) $script:servicePlanCalled=$true;throw 'Fixture service plan must not run'}
$lockPath=Join-Path $runRoot 'runtime_manager.lock'
$holder=[IO.File]::Open($lockPath,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
$held=$false
try { try { Invoke-RuntimeManager } catch { $held=$true } }
finally {$holder.Dispose()}
Assert-That ($held -and -not $script:servicePlanCalled) 'Concurrent manager entered service control'
Assert-That (-not (Test-Path -LiteralPath $registryPath)) 'Blocked concurrent manager wrote a registry'
""")


def test_registry_write_failure_blocks_before_process_creation(tmp_path):
    run_functions(tmp_path, r"""
function Get-PythonProcessInventory { @() }
function Write-Registry {param($Records) throw 'fixture registry write failure'}
$service=[pscustomobject]@{Name='fixture';WorkDir=$codeRoot;Arguments=@('fixture.py');MatchNeedle='fixture.py'}
$reason=''
try {Start-ServiceFromPlan $service @() 'C:\fixture\python.exe' $codeRoot 'fixture'}catch{$reason=$_.Exception.Message}
Assert-That ($reason -eq 'fixture registry write failure') 'Manager attempted process creation before checking registry publication'
""")


def test_stop_failure_retains_record_and_does_not_skip_remaining_service(tmp_path):
    run_functions(tmp_path, r"""
New-Item -ItemType Directory -Path $runRoot | Out-Null
Write-Registry @([pscustomobject]@{name='first';process_number=301},[pscustomobject]@{name='second';process_number=302})
$Action='stop';$StackGroup='full';$Force=$false;$Json=$false
$script:attempted=@()
function Get-ServicePlan {param($GroupName) @([pscustomobject]@{Name='first'},[pscustomobject]@{Name='second'})}
function Stop-ServiceRecord {
    param($Record,[switch]$ForceStop)
    $script:attempted+=$Record.name
    if($Record.name -eq 'first'){throw 'fixture termination not confirmed'}
}
$held=$false
try {Invoke-RuntimeManager}catch{$held=$true}
$remaining=@(Read-Registry)
Assert-That ($held -and $script:attempted.Count -eq 2) 'Failure hid an error or skipped another service'
Assert-That ($remaining.Count -eq 1 -and $remaining[0].name -eq 'first') 'Unconfirmed termination lost its registry record'
""")
