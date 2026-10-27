# LumenCore Canonical Operating State

**State date:** 2026-10-21 UTC
**Owner:** Robert Ashworth  
**Canonical product:** Proof-to-pilot AI infrastructure validation architecture  
**Work-in-progress limit:** Three founder outcomes

## One commercial sentence

### October 25 residual reviewer-gate and capacity hardening (draft)

This bounded source change advances outcome 2: reproducible reviewer evidence.
It is stacked on gateway recovery PR #259 at
`e47e5cdfb71c5c020cb65284b0421c7905426d7b`; that PR's recovery changes and
bounded timeout diagnostics are preserved. The gateway and readiness jobs
already use Ubuntu 24.04, so the earlier runner-pin edits are superseded.
The operations manual was separately rewritten on main as a proposed guide
with production `HOLD`; the obsolete whitespace-only patch is not reapplied.

The remaining gateway change checks GNU timeout admission before compilation
and adds provider/failed-version/missing/non-executable regression cases. The
existing diagnostic step, native success/hang/ignored-TERM tests, production
admission function, recovery policies and job deadline remain unchanged.
A job-scoped readiness regression protects Ubuntu 24.04 with CPython 3.11.9.

Forecast protocol validation now rejects target-count times strategy-count
budgets above 100,000 prediction rows before opening data files. The existing
10,000-target and 100,000-row limits are unchanged; exact-boundary inputs remain
accepted. Seventeen regression cases cover rejection ordering, CLI refusal,
maximum target count and the inclusive row limit. This is bounded input
admission, not a throughput, forecasting-quality or performance claim.

The initial integration's full hosted suite passed 2,282 tests and 367 subtests,
with eight skips, but failed two generated-artifact consistency checks. The
forecast edits require the existing portfolio and reviewer-packet fingerprints
to be regenerated with their unchanged builders. Preserve original timestamps,
claims and historical test receipts; these refreshed hashes are not new external
validation. The corrected commit requires a fresh complete hosted run.

Local focused tests and exact-head hosted checks are separate evidence gates.
Publication is draft-only; current-main compatibility must be established by
the hosted synthetic merge and its recorded parents. No merge, deployment,
external validation, customer acceptance or production readiness is established.
Production remains `HOLD` and existing HumanUnlock controls are unchanged.

### October 21 approved public module-type correction

Founder-approved reviewer-surface repair advances outcome 2. The exact public
release at `975dc8968b7dbc1c3a410e20a6a50584a3a9d05f` was installed by
[run 39524266446](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/39524266446).
All 246 served bodies matched their release hashes. The final gate retained a
failure at 243/246 because the three `.mjs` modules were returned as
`application/octet-stream`; seven separate service contracts passed.

The founder approved a separate correction limited to the active JavaScript MIME
mapping, a configuration test and graceful reload, full verification and a scoped
rollback. The existing read-only diagnostic now captures the active allowlisted
MIME declarations and installed module hashes, without dumping the server config.
Inspection is a prerequisite: the effective table and inheritance must be verified
before applying the four-byte extension. No DNS, credential, route, trading or
business authority is changed. The subsequent scoped repair completed in
[run 39531993525](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/39531993525):
all 246 file checks, six module checks and seven service checks before and after
the change passed. This closes the module-type release gate; the earlier failed
gate remains historical evidence. It does not resolve the separate backend holds.

### October 21 local gateway recovery correction

The October 25 allowlisted source capture increment extends the same outcome-2
private-review repair to prior-present members of the fixed gateway source bundle.
After the final source-copy admission check, the bounded evidence process validates
the pinned full inventory and selected present entry, captures source bytes and raw
required metadata through a stable descriptor, then creates the derived destination
exclusively through checked no-follow ancestors. Nested relative paths are derived
from the allowlist; callers cannot supply arbitrary paths or copy options. The
existing drop-in adapter shares the descriptor mechanics while preserving its
fixed state/destination checks. Missing and untouched source branches retain their
previous behavior, and source-result verification still follows each restoration.

Failure preserves the first source_copy result, original rollback trigger, partial
or detached files and the existing safe terminal-attempt rule. No retry or pathname
cleanup follows a failed write, metadata operation, synchronization or timeout.
The prepared inventory authenticates represented bytes, ownership, mode, mtime and
xattrs; atime is not pinned and universal cp -a equivalence is not claimed. Earlier
removal is not atomic with capture; privileged later replacement, partial earlier
restoration, outer-postcheck recovery and a hard total recovery deadline remain
unresolved. The 60-second process bound and 600-second admission origin are unchanged.
Windows integration substitutes only unsupported descriptor mechanics; native
capture/race/metadata and signal controls require Linux. At local preparation,
independent source review and exact-new-head hosted validation were pending. This
adds no production action or external validation. The separately retained two
existing drop-in admission-clock regressions were not recreated in this increment.

The October 25 fixed drop-in capture increment advances this same private-review
repair. Only a prior-present service drop-in uses a fixed, no-argument operation
inside the existing bounded recovery process. After the pinned full inventory is
validated, it captures bytes and raw extended attributes from one stable source
descriptor into anonymous private staging, limited by the prepared byte length.
It compares that capture with the prepared entry before creating the fixed target
exclusively through a no-follow directory-descriptor chain. Ownership, mode,
mtime and represented extended metadata must match on the destination descriptor;
missing platform/filesystem capabilities or any failed metadata operation refuse
success. Atime is observed for preservation but was not pinned by the prior
inventory, so this is not a universal cp -a equivalence claim.

The writer preserves partial files on write, metadata, synchronization or timeout
failure, never retries or removes a possibly replaced pathname, and retains the
original rollback trigger and first dropin_copy failure. At that preparation stage,
source-copy, missing and untouched branches remained unchanged. Exclusive creation prevents overwriting an
entry at that instant; privileged later replacement, detached-parent writes and
in-place mutation remain possible and observable rechecks are not atomic locks.
The 60-second process bound and 600-second admission policy do not establish a
hard total deadline or later external-postcheck recovery. Windows fixtures retain
actual custody/control flow but substitute unsupported writer mechanics; native
descriptor, xattr and race controls require Linux. At local preparation, source
review and exact-new-head hosted validation were pending. No production action or
external validation is established.

The October 25 drop-in pre-copy revalidation increment advances the same
outcome-2 private-review repair. When the prepared drop-in was present, recovery
now repeats the existing bounded, hash-bound state and full-inventory query after
target removal and parent creation. A fixed no-argument wrapper requires the
strictly parsed present state. The existing target-absence guard remains last
before copy. Failed launches, timeout-like status with plausible output, malformed
responses and custody drift refuse copy and later service work, retaining the
original trigger, first failure and shared parent work-admission origin.

Disposable fixtures inject backup bytes, metadata, links, type and manifest drift
at the actual removal and parent-install boundaries, rather than before earlier
validation. They also exercise failed responses, admission refusal and unavailable
terminal evidence. Earlier source restoration and drop-in removal may already
have occurred; refusal does not undo them. The safe terminal evidence attempt can
itself fail when prepared custody changed. At that preparation stage, copy still reopened a pathname after validation.
The later fixed capture increments above narrow drop-in and prior-present source
copy consumption; privileged later or in-flight mutation remains unresolved. This
adds no atomic-copy, hard total-time, whole-service restoration or later external
postcheck recovery guarantee. At local preparation, independent source review and
exact-new-head hosted validation were pending. No production action or external
validation is established.

The October 25 shared rollback admission increment advances the same outcome-2
reviewer-evidence repair. One parent-shell monotonic origin establishes a fixed
600-second engineering budget for admitting new recovery work. A bounded clock
process must finish successfully with strict framing; malformed, failed, backward
or unavailable observations refuse further work. Admission is checked before
initial validation, each checked restoration callback and each recovery service
command. At or beyond the deadline, the next operation is explicitly not started.
Original triggers and first actual operation failures retain their own status.

This is a work-admission budget, not a hard total recovery deadline. An admitted
compound callback may contain several individually bounded operations. Initial
shell path I/O, in-flight kernel work, cleanup, and terminal safety/evidence work
may exceed the budget. The parent is not killed or moved into a subshell. An
expired or unreadable clock before initial evidence validation produces no unsafe
terminal receipt. After validation, at most one terminal evidence-process attempt
may run, still behind a fresh directory guard and prepared-inventory verification;
persistence failure retains the original trigger. No later copy, service restart
or cleanup of a partial destination is authorized after admission refusal. A
result query that was not admitted leaves restoration unverified.

Disposable regressions exercise the actual controller, boundary and cumulative
clock cases, failed plausible output, each service gate, partial restoration and
terminal uncertainty. Native clock controls use only an isolated fake interpreter
with process-identity cleanup; local Linux skips do not establish signal behavior.
At local preparation, independent review and exact-new-head hosted validation
were pending. This does not solve concurrent writers, identity/check-to-use races,
uninterruptible I/O, whole-service restoration or later external-postcheck recovery,
and does not authorize production execution or claim external validation.

The October 25 recovery-directory stat increment advances the same outcome-2
reviewer-evidence repair. Its three owner/mode queries now use the preflight-checked
TERM-after-60-seconds and KILL-after-five-more-seconds policy, and require a
successful command before comparing output. A failed query with plausible output
cannot authorize the guard. Existing refusal code 13 and the original rollback
trigger remain separate; initial refusal prevents service, lock and restoration
mutations. A failed second directory guard can also prevent a refusal receipt;
the helper retains the original failure and reports that evidence is unavailable.

Disposable tests exercise the real conditional guard and rollback refusal path,
including timeout-like failed output and refusal-receipt failure. Native controls
use only an isolated fake stat executable, never production paths or services.
At local preparation, independent review and exact-new-head hosted validation
were pending. The initial shell directory/link observations remain outside the
subprocess budget. Three metadata reads are not one atomic identity snapshot;
privileged/check-to-use races, aggregate recovery timing, uninterruptible I/O,
earlier partial restoration and later external-postcheck recovery remain limits.
This does not establish production readiness or external validation.

The October 25 local control-read increment advances the same outcome-2
reviewer-evidence repair. Five rollback state and ownership-metadata reads now
use fixed selectors through the existing evidence process, with its validated
TERM-after-60-seconds and KILL-after-five-more-seconds policy. The process checks
the pinned prepared manifest and complete inventory, then compares the selected
file's captured entry to that preparation and parses those same bytes. The
selected capture is limited to 128 bytes; state and numeric metadata must use
canonical single-line ASCII representations. No caller may supply a path.
Shell readers clear prior output, require a successful query and exact response
framing, and retain the existing first-failure operation and original rollback
trigger. Drop-in state is now validated before its specific removal.

Disposable regressions interleave valid changed control bytes after all earlier
inventory checks, inject unsuccessful launches with plausible output, and retain
receipt-persistence uncertainty and earlier partial restoration. They do not
operate services or production paths. At local preparation, independent review
and exact-new-head hosted validation were pending. Per-query bounds are not an
aggregate deadline or a guarantee under uninterruptible I/O. Privileged writers
can still change targets after observation; this is not atomic rollback or proof
of complete restoration, later external-postcheck recovery or production readiness.

The October 25 local CI comparison repair advances the existing outcome-2
reviewer-evidence path. Readiness on head `aae77b54` successfully configured
Python 3.11.9, ran its verifier and 16 tests, and uploaded its bounded receipt;
its production decision remained HOLD. Public-contract and full-suite checks
also passed, but readiness and repository trust both failed their whitespace
gate on 21 lines of an operations manual. That file is byte-identical on the
tested merge and its actual main parent, and absent from the PR head. The
gates compared the older event base against a merge containing newer main.
These historical failures remain evidence, not a passing overall CI result.

Both gates now share an event-bound whitespace checker. For a pull request,
it requires checkout HEAD to match GITHUB_SHA, the exact pull-request merge
ref, exactly two commit parents, and the event PR head as the second parent.
It checks the exact first-parent-to-tested-merge tree difference, covering
PR contributions and merge-resolution changes while excluding unchanged
base-side content. The older event base is validated and reported separately,
never silently substituted for the tested parent. Push events retain the
existing before-to-checkout three-dot comparison with explicit after/ref,
non-deletion and available-commit checks. Unsupported or missing event context,
including manual dispatch without a supported change context, fails explicitly.
Git whitespace errors retain their nonzero status; no gate is bypassed, and
no unrelated manual, attribute policy or production helper is changed.

Disposable local Git fixtures exercise unchanged main-side whitespace, new PR
whitespace, merge-resolution and changed base-file defects, event/checkout or
parent disagreement, missing objects, and push refusal and success paths. They
do not mutate the application checkout or contact GitHub. At local preparation,
independent review and exact-new-head hosted results were pending. This scope
does not clean the whole base branch, authenticate all repository history,
eliminate arbitrary workflow modification risk, or resolve existing runtime
recovery, concurrency, aggregate-deadline and external-postcheck limitations.

The October 23 post-start JSON validator increment advances the existing
outcome-2 private-review repair path. Only four Python launch sites gain the
validated TERM-after-60-seconds and KILL-after-five-more-seconds policy:
generic response JSON parsing, operator denial-body validation, public-status
validation and health-body validation. Original interpreter arguments,
heredoc bodies, output redirections and comparison rules are unchanged.

The two conditional probes retain their existing twelve-attempt retries and
caller mappings: generic probes exhaust into rollback 15/16/17/18; operator
probes exhaust into rollback 19/20. Direct status and health validation retain
their original nonzero status through the actual parent-shell ERR trap and
one rollback. Plausible stdout with a failed validator cannot authorize
readiness. Inert fixtures execute the actual bodies and callers, distinguish
exact stdin and arguments, cover failure and malformed/successful payloads,
and preserve original triggers when recovery stop or terminal evidence fails.
Native controls use isolated fake interpreters, shortened test-copy budgets
and process-identity cleanup; local Linux skips do not establish native signal
behavior. At local preparation, independent review and exact-new-head hosted
validation were pending.

These four launch-site bounds are not a shared phase or total recovery
deadline: conditional retries multiply the per-launch budget. Other input,
hash, filesystem and HTTP operations, memory/output limits, uninterruptible
I/O, privileged writers, validation-to-use races, partial restoration and
recovery after the later external postcheck remain unresolved. No production
action, deployment, external validation or readiness claim follows.

The October 23 post-start metadata increment advances the existing outcome-2
private-review repair path. Only the three fixed stat queries for the service
drop-in file, runtime directory and singleton lock gain the validated TERM
after 60 seconds and KILL after five more seconds policy. Each guarded
assignment requires a successful query before comparing the existing ownership
and mode string. Expected-looking stdout followed by nonzero cannot authorize
progress. Query failure and successful but mismatched metadata retain the
existing diagnostic, ordering and explicit rollback-18 mapping, with one
parent-shell rollback and no second ERR-triggered rollback.

Inert fixtures execute the actual three blocks and ERR trap, cover every target
with statuses 1/29/124/137, malformed output, successful metadata, and actual
rollback with recovery-stop and terminal-evidence failure. Faults are scoped
to these query launches so recovery observations do not inherit them. Native
Linux controls contain only extracted blocks and a fake stat executable, with
shortened test-copy deadlines and process-identity cleanup. At local preparation,
independent review and exact-new-head hosted validation were pending; local
Linux skips do not establish native signal behavior.

Pre-mutation and inspect-only metadata reads, PID binding, recovery wrappers,
HTTP probes and later external postchecks are unchanged. These three client
budgets are not a shared phase or total recovery deadline. A successful stat is
a point-in-time observation, not stable ownership proof or protection against
privileged writers, parent replacement and validation-to-use races. Ambiguous
timeout outcomes, uninterruptible I/O, partial restoration, final service state
and recovery after the later external postcheck remain unresolved. No deployment,
external validation or production-readiness claim follows from this increment.

The October 23 post-start active-observation increment advances the existing
private-review repair path. Only the post-start systemctl is-active --quiet
launch gains the validated TERM-after-60-seconds and KILL-after-five-more
seconds policy. Its explicit rollback-18 mapping is unchanged for every
nonzero observation, including inactive, launcher error and ambiguous timeout
statuses. Plausible failed stdout cannot authorize later property checks.
The actual parent-shell ERR trap still leads to one rollback; the explicit
failure block handles this observation without a second ERR rollback.

Inert tests execute the actual block and trap, cover statuses 3/29/124/137,
success, query-specific failure during actual recovery, and terminal evidence
uncertainty while retaining trigger 18 and backups. Native Linux controls use
only the extracted block and a fake systemctl executable with shortened
test-copy deadlines and process-identity cleanup. At local preparation,
independent review and exact-new-head native hosted validation remain pending;
local Linux skips do not establish native signal behavior.

The pre-mutation and inspect-only activity observations are unchanged because
their contracts differ. This single client bound does not cancel systemd jobs,
prove final service state or establish a shared phase/total recovery deadline.
Other read/probe boundaries, privileged writers, PID/check-to-use races,
uninterruptible I/O, complete restoration and outer-postcheck recovery remain
unresolved. No deployment or production-readiness claim follows.

The October 23 forward-service increment adds fixed TERM-after-60-seconds
and KILL-after-five-more-seconds bounds to the existing forward stop,
daemon-reload, reset-failed and start launches. Stop, reload and start retain
their original strict status through the actual parent-shell ERR trap and
single rollback path. Later forward steps and state assignments do not run
after those failures. Reset-failed keeps its existing suppressed output and
best-effort continuation; its failure does not establish service readiness.

Inert tests extract the real launch lines and adjacent bookkeeping, verify
exact arguments and failure ordering, and separate injected forward faults
from the first recovery stop. Actual rollback retains the original trigger
when recovery stop or terminal evidence also fails, preserving backups and
uncertain receipts without retry. Native Linux controls use only a fake
systemctl executable with shortened test-copy deadlines. At local preparation,
native execution, independent review and exact-new-head hosted validation
remain separate gates; local Linux skips are not native behavior evidence.

These four bounds limit clients individually. They do not cancel systemd
manager jobs, prove service state, or create a shared phase/recovery deadline.
At that increment, active/inspect probes remained outside scope; the later
post-start observation boundary is described above. Aggregate budgeting,
privileged writers and state races,
uninterruptible I/O, complete restoration and outer-postcheck recovery remain
outside this change. Recovery service-command handling is unchanged.

The October 23 effective-property increment wraps the six post-start systemd
readbacks for User, Group, Restart, UMask, NoNewPrivileges and PrivateTmp with
six fixed per-query deadlines: TERM after 60 seconds, then KILL after five more
seconds. Each assignment explicitly preserves a nonzero query status and
enters parent-shell rollback once, without querying later properties or
accepting plausible failed stdout. Exact query arguments and the existing
exit-18 comparisons for successful but nonconforming values are unchanged.

Inert fixtures execute the actual phase and ERR trap, check every failing
property and query prefix, and preserve the original trigger when rollback
stop or receipt persistence also fails. Native Linux controls use only a fake
systemctl executable and shortened test-copy deadlines; local Linux skips do
not establish signal behavior. At local preparation, independent review and
exact-new-head hosted validation remain pending.

These are six per-query bounds, not one shared phase deadline. The nominal
sequential timeout envelope can reach six times 65 seconds before rollback;
uninterruptible I/O and rollback itself prevent any total-duration guarantee.
Other forward commands, aggregate recovery budgeting, PID/check-to-use races,
privileged writers, complete restoration and outer-postcheck recovery remain
outside this change.

The October 23 MainPID query increment bounds only the post-start systemd
MainPID observation with the validated 60-second TERM and five-second KILL
policy. A guarded assignment preserves the exact query failure status and
enters parent-shell rollback once, even when failed stdout resembles a valid
PID. The failed observation cannot reach lock-PID comparison, readiness
adoption or another polling iteration. Successful-query mismatch and lock-PID
reader failure still use the existing exit-18 path.

Disposable tests exercise the actual ERR trap, parent-shell rollback identity,
fixed arguments, partial output, original-trigger retention and uncertain
receipt persistence without retry. Native Linux controls contain only the
extracted query and a fake systemctl executable, with shortened test-copy
deadlines and identity-guarded fixture cleanup. Local Linux skips do not prove
native timeout behavior. At local preparation, independent review and exact
new-head hosted validation remain pending; previous-head success is separate.
That MainPID change is a per-query bound, not a total polling or recovery
deadline. The later six-property boundary is described above. PID reuse and
check-to-use races, privileged writers, uninterruptible I/O, complete
restoration and outer-postcheck recovery remain unresolved.

The October 23 owner-probe deadline increment wraps only the
`require_absent_lock_owner` Python launch with the preflight-validated GNU
timeout policy: TERM after 60 seconds and KILL after five more seconds. The
Python body and original PID argument are unchanged. Only explicit ESRCH
authorizes absence; live owners, permission/range/unknown errors and launcher
failures still refuse removal. Nonzero status, including 124 or 137 with
misleading stdout, stops cleanup before lock removal. Rollback retains its
original trigger, first failed operation and uncertain receipt outcome without
adding a retry. The post-start PID identity mapping is unchanged.

Disposable tests route the exact owner stdin body separately from the PID and
presence bodies. Malformed PID arguments reach the unchanged inert parser;
unknown, NUL-altered or newline-altered bodies refuse dispatch. All actual-body
owner signals are mocked. Native Linux controls run only the extracted probe
with a fake interpreter and shortened test-copy deadlines; they never probe a
real lock owner or run service/restoration commands. Local Linux skips are not
signal-behavior evidence, and prior-head CI does not validate this increment.

That owner-probe increment bounds one additional subprocess; the later MainPID
boundary is described above. Other forward operations and total recovery
duration remain outside those per-process bounds. PID reuse/check-to-use races,
privileged concurrent writers, uninterruptible I/O, complete restoration and
outer-postcheck recovery remain unresolved. Independent review and exact-head
hosted validation remain separate from merge or deployment authority.

The October 22 CI-budget correction changes only the public-contract job limit
from five to ten minutes. At head
`1109bbd60ac1ddc69cb377e92bc61753c812649a`, all 195 public-contract test
calls printed PASS, but the job was cancelled by its five-minute maximum after
the test step took about 301.25 seconds. Its final inspect-only/exact-hash step
was skipped, so that run did not pass the complete public gate. The independent
full suite passed 2,191 tests with eight skips and 350 passing subtests in
389.65 seconds; it does not substitute for the cancelled public gate. The
cancelled job, annotation and complete logs remain historical evidence.

The ten-minute cap leaves finite room for setup, the observed test duration,
final controls and runner variation. Tests, triggers, permissions, runtime pins
and every gate are unchanged, as are the production helper and its native
60-second TERM plus five-second KILL policy. This CI scalar does not implement
the separately proposed owner-probe deadline. No workflow rerun or deployment
is part of this correction. Successful exact-new-head hosted execution must
still include every public test and the previously skipped final control step;
the larger budget is not evidence that those checks have completed.

The October 22 lock-PID reader increment wraps only the
`read_gateway_lock_pid` Python launch with the existing validated GNU timeout
policy: TERM after 60 seconds, then forced termination after five more seconds.
Its original-byte parser, fixed lock-path argument, grammar and version checks
are unchanged. Failed subprocess output can still exist, but cleanup propagates
the exact nonzero status before owner probing or removal. Post-start identity
verification retains its existing rollback-18 mapping and never adopts a failed
PID capture. Rollback retains the original trigger and first failed operation,
stops subsequent restoration/restart and preserves uncertain receipt completion.
No retry or status reinterpretation was added.

Disposable fixtures distinguish the PID and presence readers by their exact
stdin bodies because their launch arguments match. Existing presence-stage
injections remain separate. Focused cases cover partial output with nonzero
status, both caller contracts, rollback and terminal-receipt failure. Native
Linux-only controls run an extracted PID reader with a fake interpreter; they
never run real cleanup, probes, service or recovery commands. Local skips do not
establish Linux signal behavior, and prior-head CI does not validate this change.

That increment bounded only the PID reader; the owner-probe boundary is
described above. The systemd MainPID query, other forward commands and aggregate
recovery duration remain separate. Exit 124 or 137 does not prove
a unique timeout cause. Uninterruptible I/O, privileged concurrent writers, PID
reuse/check-to-use races, complete restoration and recovery after outer
postchecks remain unresolved. Independent review and exact-head hosted evidence
are separate gates; no merge, deployment or production-readiness claim follows.

The October 22 lock-presence reader increment wraps only the
`read_gateway_lock_presence` Python launch in the existing preflight-checked GNU
timeout policy: TERM after 60 seconds, then forced termination after five more
seconds. Its Python body, lock-path argument, explicit ENOENT rule and exact-output
sentinel are unchanged. A nonzero result still prevents adoption of even a
valid-looking ABSENT or PRESENT response. Both observations around dead-lock
removal use this boundary. Failure before removal prevents that mutation;
failure after removal does not undo it or establish a successful absence check.
Existing rollback preserves the original trigger, records the first failed step,
stops later restoration and restart, and retains evidence without a new retry.

Disposable fixtures cover the fixed arguments, partial output with nonzero
status, both observation stages and terminal receipt failure. Native Linux-only
fixtures exercise a successful fake reader and hung/ignored-TERM termination
using only the extracted reader, not real recovery commands. Windows skips do
not establish native signal behavior. Status 124 or 137 remains ambiguous with
the command returning that value or another SIGKILL. That increment bounded the presence subprocess only; the PID boundary is
described above. Owner probes, all forward commands, aggregate recovery and
uninterruptible kernel I/O remain outside those two bounds. Privileged-writer races, complete restoration and
recovery after outer postchecks remain unresolved. Local and hosted results are
separate evidence; no deployment or new-head hosted result is asserted here.

The October 22 target-version reader increment applies the preflight-checked GNU
timeout policy of 60 seconds plus five seconds before forced termination to the
single `recorded_target_version` Python subprocess. Its embedded Python checks,
arguments, fixed-object/source allowlists, version representation and absence
queries are unchanged. The shared boundary covers source, service drop-in,
runtime-directory and drop-in-directory observations in both forward readback and
recovery. A nonzero result remains a failure even after valid-looking output;
callers must not adopt it or advance a pending write to installed. Existing
first-failure handling stops subsequent restoration and restart, retains the
original trigger and preserves any already-partial state and recovery evidence.

Reader diagnostics report observation UNKNOWN and no retry. Exit 124 remains
ambiguous between deadline expiry and that command exit; 137 remains ambiguous
with another SIGKILL. Inert launcher fixtures exercise exact arguments, failed
capture/absence queries, actual forward transitions and receipt failures. Two
Linux-only fake-reader fixtures cover native success and hung/ignored-TERM
termination with identity-checked cleanup; they do not run real recovery commands.
This single-process policy does not bound other lock readers, probes, forward
commands, uninterruptible kernel I/O or aggregate recovery duration. It does not
eliminate privileged-writer/check-to-use races or establish complete restoration
or automatic recovery after external postchecks. Focused local validation passed
seven tests with the two native Linux cases skipped on Windows. At local
preparation, independent source review and exact-new-head hosted validation were
pending; the earlier head's passing checks do not validate these new bytes.

The October 22 recovery-evidence increment applies the preflight-checked GNU
timeout policy of 60 seconds plus five seconds before forced termination to the
single `record_recovery_evidence` Python subprocess. A shell allowlist covers its
ten existing receipt, verification and result-query kinds. Its Python arguments,
receipt schema, exclusive publication and readback checks are unchanged. A
nonzero subprocess result is returned unchanged even after partial stdout;
existing callers refuse it before proceeding or preserve the original rollback
trigger. Preparation still finishes before forward runtime changes.

The failure diagnostic separates the evidence kind and numeric exit from service
or filesystem-mutation failures. Exit 124 remains ambiguous between deadline
expiry and that command exit; 137 remains ambiguous with another SIGKILL. A
writer may publish before failing or terminating, so evidence completion is
UNKNOWN, all existing files remain, and no retry or replacement is attempted.
The fixed deadline applies to this subprocess, not all other readers, probes,
staging operations, forward commands or overall recovery. Uninterruptible kernel
I/O, privileged writers, check-to-use races, complete restoration and automatic
recovery after external postchecks remain unresolved. Disposable fixtures check
normal receipts, nonzero results with valid output and before/after-publication
failure. Separate Linux-only fake-writer fixtures check native termination and
ignored TERM; their test-copy deadlines are shortened without changing production
policy or running real service/filesystem repair commands. Focused local
validation passed nine tests with the two Linux-only tests skipped on Windows.
Those native process/signal cases remain unexecuted locally. Independent source
review found no blocking findings. Hosted validation was pending at preparation;
prior hosted results did not establish exact-new-head validation.

The October 22 target-filesystem command increment routes the ten remaining
rollback mutation sites through one operation/target allowlist: dead-lock and
source/drop-in removal, fixed drop-in parent creation, and ownership, mode and
empty-directory removal for the two fixed directories. The wrapper derives the
exact command and path from those identifiers, with no caller-supplied command,
recursive removal, retry or deadline override. It reuses the preflight-checked
GNU timeout policy of 60 seconds plus five seconds before forced termination.
The shared dead-lock cleanup also applies this command limit in the forward path.
Existing copy and service limits, state/version guards, custody verification and
result queries remain unchanged.

The first failed command still stops later restoration and service restart while
preserving the original trigger. Failure receipts name a deadline only when the
allowlisted wrapper was actually reached; an earlier lock read, owner-probe or
later absence-query failure is not mislabeled as a bounded mutation failure.
Forward mutation failure markers are cleared when rollback begins. A command may
change its target before failing or terminating; its effect remains unverified.
Exit 124 cannot distinguish deadline expiry from a command returning 124, and
137 cannot distinguish forced timeout termination from another SIGKILL.

Validation uses inert command/launcher stubs and disposable files, including
exact argument rejection, every mutation site, after-effect failures and retained
receipt/original-code behavior. These controls do not establish native elapsed
time or signal delivery. They do not bound Python reads, probes, hashing, receipt
persistence, all forward commands or total recovery duration; uninterruptible I/O
can also exceed the nominal policy. Privileged writers, check-to-use races,
complete restoration and automatic recovery after external postchecks remain
unresolved. The affected-path local run passed 17 tests; standard-library import
found 168 tests and executed none. At local preparation, exact-new-head CI and
independent source review were pending.

The October 22 lock-cleanup increment adds one fixed-path presence observer at
the initial skip decision and after a successful removal command. Only an
explicit ENOENT from trusted-Python lstat establishes absence; all present
objects, including dangling links, remain present and other observation errors
refuse. Strict output framing rejects malformed results and preserves interpreter
failure. Existing binary PID parsing and ESRCH-only owner classification remain.
A removal command reporting success while leaving or recreating a lock now stops
later restoration and restart through the existing first-failure receipt path,
retaining the original trigger and visible receipt-persistence failures. This is
a point-in-time absence observation, not object ownership or atomic deletion.
PID reuse, lock/parent substitution before removal, later reappearance and
validation-to-use races remain; whole restoration, overall I/O duration and late
external-postcheck recovery remain unverified. Controlled inert fixtures are
local validation, not evidence of a native removal or production incident.
Exact-new-head hosted validation and independent source review are pending.

This source-only follow-up advances outcome 2 by correcting a failure path in the
existing gateway repair control. Twelve post-change checks now call rollback
directly instead of exiting past the error handler. Rollback disables its error
trap and ignores INT/TERM during recovery so a failed restoration or another
termination signal cannot re-enter recovery or replace the original failure code.
Subprocess regression cases execute the actual guards and rollback function
against disposable files, including failed restoration and TERM during recovery.

The same source-only correction now retains recovery files in a unique private
directory under `/var/backups/lumencore-gateway-repair` after every exit. Existing
unsafe directories are refused without repairing their permissions. A private,
hash-bound manifest and its readback must finish before runtime mutation; immutable
outcome receipts distinguish helper checks passed with external verification
pending from rollback attempted without verified restoration. Receipt persistence
failure remains a non-success outcome. A later workflow postcheck cannot remove
these retained files through the helper's cleanup path.

Before the first restoration command, rollback now verifies the prepared manifest
and its source bindings, exact present/missing inventory, file hashes and recorded
metadata. Unsafe links, altered files and unexpected inventory cause refusal before
service, lock or installed-file changes. A private refusal receipt states that no
restoration was attempted; the original failure code and retained evidence remain.
Refusal leaves any earlier partial runtime change unresolved. This verification is
a point-in-time check and cannot prevent a later concurrent edit.

The next local increment bounds only rollback's four service-control commands:
stop, daemon-reload, reset-failed and conditional start. GNU timeout availability
is checked before forward runtime mutation. Each command has a fixed 60-second
limit and five-second forced-termination grace, with no retries. An unconfirmed
stop prevents lock and file restoration; a later service-command failure stops
the remaining service sequence. Private receipts retain the original failure code,
attempted command outcomes and unverified service/restoration status. Exit codes
that could come from either the launcher or command remain explicitly ambiguous.
Terminating a systemctl client does not prove cancellation of its systemd job.

The next local increment checks each rollback lock, file, metadata and directory
operation explicitly. The first failure stops all later restoration work and the
service reload/reset/start sequence. Lock-content read and inner removal failures
cannot be hidden by a later successful message. Missing-before directories are
removed only when empty; unrelated contents are retained. The private failure
receipt names an allowlisted operation and target, records its exit code separately
from the original trigger code, and marks partial state and unverified restoration.
If changed backup evidence prevents receipt persistence, that failure stays visible
and the original nonzero result and remaining recovery files are preserved.

Source restoration intent now comes from the pinned preparation manifest's
present/missing inventory, with a read-only source-state query before target
removal and again before copying an originally present source. Each query repeats
the full source/schema/inventory/hash/metadata validation and accepts only an
allowlisted relative path with exact response bytes. A vanished backup cannot be
reinterpreted as an originally absent source, and altered or newly introduced
backup data stops later restoration and service restart. A change after an earlier
file was restored or after target removal still leaves explicitly partial state;
receipt integrity checks remain intact even when they prevent receipt persistence.
Repeated validation over a bounded file set is not a wall-clock deadline.

The next source-only increment records actual forward installation progress for
each source: untouched, write pending, or installed with a stable version digest.
Candidate hashes come from the approved source manifest and are checked against
staged files before runtime mutation. The installed version is recorded only after
successful installation and matching candidate readback. Before source removal,
rollback compares bytes, regular single-link identity, ownership, mode, timestamps,
extended attributes and stable parent identity with that recorded version. Parent
directory timestamps are excluded because this invocation changes sibling entries.
An unknown state, incomplete write or changed target stops remaining restoration
and service restart without removing that target. Untouched sources are skipped;
their present state is not certified. A target that reappears after removal is
refused before backup copy. Private outcomes include per-source state and digests,
while retaining the original failure code, partial-state warning and receipt
integrity checks. Earlier restored files can still leave partial state.

Source recovery now also checks the observed result after each installed source's
removal and optional backup copy, before the next source or service sequence.
The read-only result query repeats pinned custody validation, then checks stable
regular single-link target bytes, ownership, mode, modification time and extended
attributes against the prepared inventory, or confirms actual absence for a
missing-before source. Copied inode and change time may differ from the backup;
their stability during this read is still required. Parent identity and safe path
checks are included. A command returning zero with an absent, incorrect or unsafe
result stops later restoration and restart. This closes the controlled fixture
case where a copy reported success without producing the required file; it is
not evidence that the real copy utility or production runtime suffered that fault.
Private receipts distinguish each matched observation, failed result query,
unchecked untouched source and source not yet checked. They retain partial-state
and whole-restoration/service-unverified status, even when every source observation
matches. Later edits, other restored objects and external workflow checks are not
certified by these observations.

The single service drop-in file now has a separate result check immediately after
its removal or backup copy, before later directory metadata and service recovery.
The fixed-object query accepts no source path, repeats pinned custody validation,
and derives prior presence from the prepared inventory. A present result must
match stable regular single-link bytes and preserved metadata; a missing-before
result must actually be absent, including no dangling link. An already absent
immediate parent is allowed only with safe existing ancestors and stable parent
observations. Failure stops later recovery, preserves the original trigger and
prior partial source observations, and leaves any receipt persistence failure
visible. The private receipt labels this as a file-only observation. Directory
metadata, effective service configuration and whole restoration remain unverified.
The motivating disposable fault reports copy success without restoring the drop-in;
it is not evidence of a native copy-command or production failure.

The next source-only increment adds a separate result check for the fixed runtime
directory after its existing metadata restoration or empty-directory removal,
before service reload/reset/start. It repeats pinned recovery-evidence validation
and parses the exact captured state/metadata bytes that match the prepared
inventory. A present result must be an actual stable directory with the recorded
numeric owner, group and mode; a missing result must truly be absent, including
no dangling link. Safe parent observations are included. Failed or malformed
queries use the existing fail-stop receipt path, retain the original trigger and
earlier partial source/drop-in observations, and prevent later service commands.
Nonempty missing-before directories remain preserved with recovery stopped.

The private receipt records this directory's narrow observation separately;
restoration and service verification remain false. It does not certify directory
contents, timestamps, extended attributes, ACLs, exclusive ownership, earlier
inode identity or later state. The motivating disposable removal stub reported
success while leaving an empty originally-missing directory, yet the prior helper
reached restart. That is a controlled fault injection, not a native-command or
production incident. Initial local failures exposed Windows fixture CRLF bytes
where production emits LF; fixture preparation now uses explicit LF, without
relaxing the production parser. The failed run and diagnostic remain preserved.

The service drop-in directory now has its own fixed result check after its existing
metadata restoration or empty-directory removal, before any runtime-directory
restoration or service restart. Its no-path query repeats pinned recovery-evidence
validation and parses only captured state/metadata bytes matching the prepared
inventory. It requires a stable actual directory with the recorded numeric owner,
group and mode, or true absence including no dangling link, with safe parent
observations. Wrong results and malformed queries stop later recovery through the
existing first-failure path; the original trigger, earlier partial observations,
retained backups and visible receipt persistence failures remain. Nonempty
missing-before directories are still preserved and refused. The separate receipt
observation does not certify contents, timestamps, ACLs, extended attributes,
exclusive ownership, effective service state or whole restoration. The motivating
disposable removal stub returned success without removing an empty originally
absent directory; that controlled fault is not a native-command or production
incident.

The next local increment protects the fixed service drop-in before rollback
overwrites it. Its actual forward file installation now records untouched, write
pending, or installed state. The already approved hardening digest is pinned and
checked against staging before runtime mutation; an installed version is captured
only after successful installation and matching stable readback. The existing
source version reader is shared through an explicit fixed-object dispatch, without
allowing a caller-selected drop-in path or changing the source query interface.
Before removing the drop-in, rollback compares its current bytes, regular
single-link identity, ownership, mode, timestamps, extended attributes and stable
parent identity with that recorded version. Unknown/partial writes and conflicts
stop later file, directory and service recovery while preserving the target and
original failure code. A reappearing target is refused before backup copy.
Untouched drop-ins are skipped and explicitly unchecked, rather than certified.

The motivating disposable case changed only the drop-in after recovery stop;
the earlier helper overwrote that edit and reached service start, despite honestly
retaining whole-restoration-unverified status. The regression executes actual
forward transitions and recovery functions, with service/ownership operations
stubbed and files confined to temporary fixtures. This is not a production incident.
The new guard remains a point-in-time observation: an intervening privileged
writer before installed-version capture can be adopted if approved bytes still
match, and validation-to-use intervals are not atomic. Directory ownership,
source-backup races, filesystem/total-recovery deadlines and outer postcheck
recovery remain unresolved. No backend production repair or merge is authorized
by these local results.

This increment passed 136 focused local tests with 11 platform skips. The separate
dependency-free runner passed 117 checks with the same 11 skips (128 discovered);
the overlapping counts are not additive. Both runs bound unchanged helper and
test hashes. Initial selected coverage retained one assertion failure: the fixture
represents an unparsable collision receipt as null, rather than omitting its key.
Only that assertion was corrected; original failure-code and evidence retention
already worked. Final independent source review found no blocking issue. Committed head
4905be42 subsequently passed all 14 hosted checks: 128 Linux public-contract
checks without skips and 2,124 full-suite tests with eight unrelated skips and
350 passing subtests. Both jobs checked out merge ba2cd218, whose parents are
fresh main 2d82be53 and that exact head. The provider still reports the older
PR-base metadata; the actual tested merge parents take precedence for this claim.

The next local increment protects only the fixed runtime directory before rollback
changes its ownership/mode or removes it. Expected numeric service owner/group and
mode0750 are pinned before forward runtime mutation. The actual directory install
records untouched, write pending or installed state, with a stable directory and
parent identity digest captured only after matching readback. Rollback checks that
version before this object's first restoration operation. A changed, missing,
replaced, linked, unknown or partially installed directory stops later recovery,
preserves the original failure and remaining evidence, and prevents service restart.
An untouched directory is skipped and explicitly unchecked. The existing narrow
post-result query and nonempty-directory refusal remain in place.

The motivating disposable baseline replaced an empty originally-missing runtime
directory after recovery stop; the previous rollback removed that replacement and
reached restart. It is a controlled interleaving, not a production incident. The
guard binds type, device/inode, numeric owner/group, mode and stable safe parents.
Child counts and directory timestamps are excluded because this invocation and
the service can legitimately change lock/child entries. It does not certify
contents, ACLs/xattrs, exclusive ownership or whole restoration. Windows fixtures
substitute only the unavailable Unix-mode comparison; actual mode/link behavior
requires hosted POSIX validation. Privileged install/readback and check-to-use
races, prior partial source/drop-in/lock restoration, the other directory's
ownership, overall filesystem deadlines and outer postcheck recovery remain
unresolved. No backend deployment or merge is established by this draft.

Final affected-path validation passed 10 local tests with 1 POSIX-only skip,
including the actual RUN_DIR transitions, the amended install contract and adjacent
source/drop-in controls. All three public-contract files also imported under
Python without site packages (134 tests discovered; none executed by that import
check). The initial five-file and three-file runs were stopped after the known
obsolete direct-install marker failed: they remain interrupted, incomplete results,
not successful suites. The focused log showed 42 pass, one fail and six skip markers;
the dependency-free runner last reported 40 completed with one failure. The static
assertion now requires the numeric pinned install and actual guarded forward call;
no production guard was relaxed. The selected final run binds unchanged helper and
test hashes; Bash syntax and diff checks passed. These overlapping local observations
are not additive and do not replace exact-new-head hosted Linux validation, which
remains pending for this revision.

The completed runtime-target draft at `ee0aeb12` subsequently passed all fourteen
hosted checks. Its actual merge checkout `02bb5e73` has parents main `2d82be53`
and that exact draft head: 134 Linux public-contract checks passed without skips,
and the repository suite passed 2,130 tests with eight unrelated skips and 350
subtests. Those are completed historical results, not validation of the next edit.

The October 22 source-only increment advances outcome 2 and protects the fixed
service drop-in directory before rollback can mutate it. Expected numeric
root:root ownership and mode0755 are fixed before forward writes. The actual
directory install records untouched, write pending or installed state; only
successful matching readback records a stable directory/parent version. Unknown,
partial, missing or changed state refuses recovery before the child-file work,
before rollback's separate parent-install command, and before the later directory
ownership/mode/removal branch. Untouched parent and child must be consistent;
they are skipped and explicitly unchecked, not treated as restored. The existing
nonempty refusal, prepared-inventory verification and narrow result observation
remain in place. Original trigger status and retained evidence survive refusal,
while earlier source or child restoration may already have left partial state.

The preserved disposable baseline replaced an empty directory after the drop-in
file result check; the old helper removed the replacement and reached restart.
That is a controlled interleaving, not a production incident. New fixtures execute
the actual forward transitions and both guarded rollback sites. Directory
timestamps and child counts are excluded so this invocation's child changes do
not appear as conflicts. Root ownership is substituted only in unprivileged test
fixtures, and Windows additionally substitutes its unavailable Unix-mode read;
actual mode/link behavior still requires exact-head hosted Linux validation.
Privileged install/readback and validation-to-use races, directory contents,
ACLs/xattrs, whole restoration, an overall filesystem deadline and recovery after
a later workflow postcheck remain outside this increment. No deployment or merge
is authorized by these local source changes.

The final affected-path run passed ten local tests with two POSIX-only skips,
covering the new directory guard and adjacent source, runtime-directory, fixed-file
and deployment-contract controls. Three public-contract modules imported without
site packages, discovering 140 tests but executing none in that import check.
Bash syntax and diff checks passed. The first new-case run retained four passes,
one platform skip and one fixture assertion failure: a deliberately unreadable
rollback receipt is represented by a null entry, not a missing key. The assertion
was corrected; the original failure, original exit status and no-restart evidence
remain preserved. No production guard was relaxed and no broad overlapping suite
was repeated. Independent review and hosted validation subsequently passed at
`6ba9e37d`: fourteen checks, 140 Linux public-contract checks with no skips, and
2,136 repository tests with eight unrelated skips and 350 subtests. The tested
merge used public main `2d82be53` and that exact draft head; the provider's older
PR-base field was retained as a metadata discrepancy. Those historical results
do not validate the following workflow edit.

The next outcome-2 increment records runner-side evidence when the existing
external postcheck starts and terminates. It binds the release, bundle, hardening,
run and attempt identifiers to the retained helper stdout and its reported private
outcome hash; it does not independently read the private helper receipt. The
started record means the external result is unknown. A terminal record identifies
the active request or assertion stage, whether it began/completed, the completed
stage prefix and original exit status. Existing public contract probes, exact-main
gate and authorization controls are unchanged. Both records join the existing
always-upload artifact list; raw response bodies and credentials are excluded.

First/later probe or assertion failures retain their original nonzero status even
if outcome persistence fails. Successful checks followed by failed persistence
instead fail the step. Signals produce an interrupted/unknown result when the
exit handler can run; abrupt runner loss may leave only the started record or no
record, so absence never proves success. Ordinary failed workflow logs remain
evidence too. These records neither invoke restoration nor establish service
state, production readiness or whole recovery. Later recovery still needs a
separately reviewed interface and action-time authorization; overall filesystem
deadlines, privileged races and artifact upload/durability limits remain open.

Eight selected local tests passed, including actual extracted workflow execution
with inert HTTP/JSON stubs for first/later failure, full success, interrupted and
incomplete exits, invalid helper binding and receipt-persistence failures, plus
adjacent retained-backup and unchanged-gate controls. The stubs test workflow
control flow and evidence behavior, not live HTTP responses or JSON-tool
integration. There was no production action and no baseline reproduction rerun.
The three dependency-free public-contract modules imported with 145 tests
discovered and none executed; extracted-step Bash syntax and diff checks passed.
Independent review and hosted validation subsequently passed at `145def3b`:
all fifteen checks, 145 Linux public-contract checks without skips, and 2,141
repository tests with eight unrelated skips and 350 subtests. Its tested merge
used public main `2d82be53` and that exact head. The reviewed workflow's CRLF
working bytes normalized exactly to the committed LF bytes; tests and this note
were byte-exact. Those results are historical, not validation of the next edit.

The next outcome-2 source increment bounds only the two rollback copy call sites:
each source-backup copy and the fixed service-drop-in backup copy. Each invocation
uses the already preflighted GNU timeout with a fixed 60-second limit and five-second
forced-termination grace. There is no retry or caller-selected duration. Existing
custody, source intent, target version, true-absence and post-copy result checks
remain in place. A nonzero copy/launcher result uses the existing first-failure
path, stops later restoration and service commands, and preserves the original
trigger status separately from the copy status. A partial destination is retained
as unverified. Private failure metadata states the fixed budget and preserves
exit124 and exit137 ambiguity; neither code uniquely proves a timeout cause.

The prior disposable Windows hang harness failed its own cleanup and was not a
qualified reproduction; its exact identified process was subsequently stopped
and absence verified. This increment does not rerun that harness. New bounded
fixtures use an immediate-return launcher stub to exercise actual rollback paths,
exact command arguments, first/later copy failures, partial destinations, ordinary
command status, receipt-write failure and successful copy result checks. They do
not demonstrate real copy elapsed-time or signal behavior. Four new tests and
six selected adjacent/preflight controls passed in two bounded local invocations,
with no failures or skips. Three public-contract modules imported without site
packages, discovering 149 tests and executing none during that import check.
Bash syntax and diff checks passed. Exact-head validation of the subsequent
correction is recorded below; no merge or production operation is established.

Initial hosted head `285e6c0a` failed the public-contract job before the new copy
cases: the older deployment-contract assertion still required the previous direct
drop-in copy spelling. That assertion now requires the exact bounded call with the
fixed backup/target arguments, plus the wrapper's two-argument guard, fixed timeout
policy and `cp -a --` ordering. The runtime helper is unchanged by this test-only
correction. Initial failed CI evidence remains preserved; the previous selected
local results did not cover this static contract. The full hosted suite retained
the same single assertion failure, 2,144 passes, eight unrelated skips and 350
subtests. After the test-only correction, the exact static contract plus the four
new copy tests passed locally (five passes, no failures or skips); these overlap
the initial selected results and are not additive. Corrected head `f207a725`
subsequently passed all fifteen checks, 149 Linux public-contract checks without
skips, and 2,145 repository tests with eight unrelated skips and 350 subtests.
The tested merge used public main `2d82be53` and that exact head. The failed first
head remains preserved; these completed results do not validate later edits.

The current outcome-2 draft narrows singleton-lock cleanup to an explicit process
absence observation. A Python signal-zero probe authorizes removal only when its
error number is ESRCH. A live process, permission denial, invalid or out-of-range
PID, other probe errors and interpreter failures refuse removal. ASCII decimal
syntax and a ten-digit bound are checked before conversion; the positive signed-32-bit
range is checked before any probe. The fixed lock path and existing read, link and removal checks remain in
place. The shell requires the interpreter's successful classification, retains
its nonzero status otherwise, and uses the existing first-failure rollback path:
no later restore/service work follows refusal, the original trigger status is
preserved separately, and lock, target and recovery evidence remain available.

Deterministic fixtures execute the actual embedded classifier and extracted
rollback while replacing only its process probe. They exercise explicit ESRCH,
live/permission/invalid/unknown classifications, argument bounds, interpreter
failure, refusal with receipt-write failure, valid/absent locks and adjacent
restoration controls. No native Windows process signal or hanging fixture runs.
The first selected invocation retained four passes, two failures and one POSIX
skip: an old error-message assertion and a trailing-newline argument crossing
the Windows/MSYS fixture boundary. The static assertion now requires the new
message and exact classifier call; the newline case executes the same embedded
Python body directly and verifies rejection before probing. The final bounded
selection passed six tests with one POSIX-only skip. The two invocations overlap
and are not additive. The three dependency-free public-contract modules imported
with 152 tests discovered and none executed. Bash syntax and diff checks passed;
independent review and exact-new-head hosted CI remain pending.

ESRCH is only a point-in-time absence observation. This does not establish that a
lock was historically owned by that PID, eliminate PID reuse or lock replacement
between checking and deletion, or verify complete recovery. Permission failures
may be uncommon under the production root identity; this corrects classification,
not a demonstrated production incident. Existing aggregate deadlines, privileged
writer races, partial-restoration and external-postcheck recovery limits remain.

The resulting head `ce968a07` subsequently passed all fifteen hosted checks:
152 Linux public-contract checks without skips and 2,148 repository tests with
eight unrelated skips and 350 subtests. Those completed results belong to that
head and do not validate the following local increment.

The next outcome-2 increment replaces both lock-file whitespace-normalization
reads with one no-argument reader of the fixed approved lock path. It reads at
most thirteen binary bytes and accepts only a positive ASCII decimal PID of at
most ten digits and signed-32-bit range, optionally followed by exactly one LF
or CRLF. Original internal whitespace, extra lines, NUL, Unicode, signs, leading
zeros, oversized records and invalid ranges are refused before a process probe
or removal. The reader requires a regular file and checks stable file identity,
size and timestamps across its bounded read; available no-follow/nonblocking
open flags prevent following a final symlink or waiting on a substituted FIFO.
Only validated canonical decimal output reaches the shell. Cleanup preserves
reader/classifier failure status through the existing fail-stop path. The actual
post-start identity check uses the same reader and calls rollback with its
existing failure code on a read/grammar error. ESRCH-only removal authorization,
recovery evidence and original-trigger preservation remain unchanged.

Ten selected local tests passed with one POSIX-only symlink case skipped in one
executable invocation. Actual extracted cleanup and post-start code consume exact
file bytes; process probes, systemd, polling delays and rollback side effects in
those small fixtures are inert. Separate actual-rollback fixtures establish that
malformed bytes stop later restoration/restart and preserve the original trigger,
including receipt-write failure. Existing ESRCH, valid/absent-lock, read/removal
failure and deployment contracts were included. The three dependency-free modules
imported with 157 tests discovered and none executed; syntax and diff checks
passed. The previous optional inert diagnostic remains a failed, unqualified
attempt and was not rerun. Independent review and exact-new-head hosted validation
remain pending; no merge or production operation occurred.

This grammar check is not atomic ownership protection. A service can be observed
mid-write and safely refused, and PID reuse, parent/lock replacement and the
read/probe/removal intervals remain races. The bounded byte count is not a total
I/O or recovery deadline. Earlier partial restoration, privileged writers, whole
restoration/service verification and later external-postcheck recovery remain
unresolved.

Only copy invocation duration is addressed. Source/target queries, filesystem
removal and metadata operations, receipt writes, cleanup and aggregate recovery
duration remain unbounded. Uninterruptible kernel I/O or scheduling can prevent
prompt process termination. Privileged validation-to-use races, earlier partial
restoration, whole-restoration verification and later external-check recovery
remain unresolved.

The preceding runtime-directory revision at `2e0fdcb8` passed all 14 hosted checks:
114 Linux public-contract checks with no skips and 2,110 full-suite tests with eight
unrelated skips. It included actual GNU timeout process-group, ignored-TERM,
descendant-termination and link/extended-attribute cases. The service drop-in
directory increment passed seven selected local tests with one platform skip,
then 129 focused local tests with ten platform skips. The dependency-free runner
passed 110 checks with the same ten skips (120 discovered). Independent final
review and exact-head hosted Linux validation of that increment subsequently passed:
head `15c53f3c` has 14 successful checks, 120 Linux public-contract checks with no
skips, and 2,116 full-suite tests with eight unrelated skips. Those checks tested
merge base `50969f7f`; the freshly observed public main is now `2d82be53` and that
new-main combination has not been established by those prior runs. Validation of
the new fixed-drop-in target guard is recorded separately and does not inherit
the prior head's CI success. The
initial local strict-query failure in the earlier revision exposed platform newline
translation; exact byte output corrected it without relaxing response parsing.
Local subprocess cases execute actual rollback operations against disposable files,
including failures before and after earlier files were restored. No backend repair was
dispatched or installed. This does not establish deployment readiness: restoration
remains best effort, there is no verified restore API for a later public postcheck
failure, and concurrent-state protection remains incomplete. The guard addresses
the reproduced target-only edit observed before recovery removal; it cannot close
the install/readback or backup/target validation-to-use intervals against a
privileged writer. Forward target writes, service configuration and runtime-directory
state are not covered by an atomic transaction. Parent replacement after removal
and the last absence-check/copy interval remain unprotected; the absence query
does not bind an atomic restoration to a directory handle. A version digest does not establish
exclusive ownership, complete restoration or full concurrency protection.
File, metadata, lock,
evidence and cleanup operations still lack comprehensive deadlines; the four
service-command budgets are not a total rollback deadline. File and top-directory synchronization does not prove
power-loss persistence of every nested backup entry. The existing six runtime holds
require fresh evidence and separate backend action approval. Paper-only controls
and all ledger/history bytes remain unchanged.

### October 17 draft integration review

The founder requested inspection, safe merge and publication of outstanding
repository work. The review inventoried all 24 open PRs at main
`e706e91de133e039cc16ed25ec5021a293edbf2b`, including 16 drafts. Main was
reproduced locally on CPython 3.11.9 with the 39-package institutional hash lock:
1,914 tests and 343 subtests passed, with eight documented skips. This Debian
cloud run is current-source verification, not the frozen scientific runtime
or live trading evidence.

The buyer-owned replay integration preserves declared timing as unverified
custody and favorable numerical results as HOLD. Adversarial review found that
a predictable temporary receipt filename could delete a frozen input or follow
a pre-existing symlink. The repair uses an exclusively created temporary file,
rejects output aliases to any input, and cleans only its own temporary file.
Input-preservation and failed-replacement regression cases are retained.

Source integration and website installation remain separate. The October 17
11:29 UTC [scheduled audit](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/39028831382)
for e706e91 recorded 190 of 246 exact matches, five mismatches and 51 HTTP 404s.
The manual exact-snapshot VPS workflow, signed archive checks and rollback
capture remain the deployment path. No runtime, DNS, credential, financial
authority or live-order gate is changed by this source review. Exact hosted
checks and merge receipts must be recorded for the resulting commit.

### October 14 authorized merges and paper-readiness repairs

The founder explicitly requested review and merge of compatible draft changes
and further trading-readiness work. PR #253 merged at
`22dc828ccabc3d14accbc9b3e3f3316b8d2f6464`, retaining the exact source tree whose
15 applicable workflows passed. Its hosted full suite recorded 1,773 tests and
307 subtests passing with eight documented skips. This is first-party source
verification; no runtime installation or real-money order authority follows.
PR #203's coordinated CodeQL update then merged at
`7d871ccdcbd59b2ebb200773470f165e2f918cce` after all seven applicable workflows
passed, including 1,774 tests and 307 subtests with eight explicit skips.

The existing PR consolidation map records the triage of the 25 other drafts
inspected after #253, including #203. This bounded source
pass tightens paper startup flags, candle chronology/freshness, confirmed-fill
accounting, paper timestamp acceptance and public-health validation. The active
paper reader and executor facade exclude retrospective rolling research from
execution preferences; archived consumers retain their original bytes. Unknown
unrealized profit and unreconciled returns remain unknown in the report and
display. The readiness dossier now names the unresolved fill, account,
daily-risk, after-cost performance and runtime-evidence
requirements. Local fields labeled live, filled, measured or daily cannot close
those requirements by themselves. Paper mode, order blocks and production HOLD
remain; no broker connection, order, credential or financial-control activation
is performed by this continuation.

### October 14 bounded reviewer continuation

Founder-directed archive recovery and repository preparation advance outcome 2,
one bounded external evaluation or paid scope. The existing reviewer guide now
organizes code quality, security, scalability and launch-effort questions, with
written finding fields and separate commercial authority. Reviewer identities,
private correspondence, shared attachments and proposed commercial terms remain
outside this public repository. An existing shared packet does not require a
duplicate send, and proposed review terms do not establish completed validation.

The clean baseline at `3c61648e593e5e036681f9c32dd82bce18ef3970` passed 1,684
tests and 224 subtests with eight explicit skips on CPython 3.11.9 using all
39 packages from the institutional hash lock. This local host is Debian 13,
glibc 2.41, not the Ubuntu 24.04/glibc 2.39 frozen scientific runtime. It is a
current-source first-party check; the subsequent repairs require their own
exact-source verification. Missing generated artifacts, optional native C and
Windows-only checks are not counted as passing execution.

The continuation closes alternative private-order route acceptance, ambiguous
mutation retries and malformed CSV/token exception paths with offline regression
fixtures. No broker, market feed, live worker or production configuration is
activated. These repairs do not close historical strategy-selection bias,
fee/fill/latency assumptions, account reconciliation, legacy provider closure,
live release drift or prospective operating-evidence gates.

The founder-requested follow-on continues in the same draft review change. It
aligns mounted/proxy-root authorization with the router, rejects timestamp
precision that would be silently truncated and bounds v2 seasonal-history
lookups. Ledger recovery restores all verified missing CSV projections before
accepting another event; the spot-return engine rejects impossible underlying
losses below -100%. The local dashboard now separates configured intent,
reported counts, modeled dollar rates and unverified source observations. The
browser bridge labels poll attempts and report values without implying source
freshness, and the refresh lock no longer expires an active owner's claim after
six hours. Offline regression fixtures reproduce the prior failures. These
source fixes do not establish their deployment, data freshness, reconciliation,
operating benefit or institutional throughput. The existing review packet and
tracked-file portfolio inventory are refreshed from the resulting source.

The archive review distinguishes recovered files and indexed historical records
from unavailable device roots and unreviewed images. The early infrastructure
loop uses assumed gains and dollar rates; the legacy constraint detector uses
modeled provider failures. Their displays cannot establish savings or revenue.
Frozen scientific inputs, outputs, runners and dated results remain unchanged.
Whole-estate reconciliation remains OPEN. The next commercial gate remains one
authorized buyer problem, technical and budget owners, accepted scope and
required payment, followed by a bounded delivered result and buyer acceptance.

### October 13 reviewer-readiness and trading repairs

Founder-authorized current-source repairs advance outcome 2: one bounded external
evaluation or paid scope. The scope includes forecasting/evidence acceptance,
ProofLock identities, gateway serving controls and the existing trading research
lane. It does not authorize live orders, autonomous control, paid reviewer terms
or a scientific performance promotion.

Receipt acceptance now reconciles the original five frozen-input assertions and
26 suite assertions against the immutable protocol, including failed promotion
facts and the later packet's referenced environment identity. Frozen scientific
runners, inputs, outputs and dated receipts remain unchanged. The executable v2
forecast doorway instead reviews supplied forecasts under a separately pinned
protocol, requires complete calendar/as-of comparisons and preserves dependent
and adverse results in HUMAN_REVIEW_HOLD. Its included fixture is synthetic.

ProofLock adds explicitly versioned binary64/scalar Unicode serialization and
real JavaScript/Python parity checks. The historical portable v1 example retains
its bytes; nonportable v1 inputs reject. Private output routes are protected by
the operator boundary; nginx source no longer aliases the full output directory
as a public proof surface. Malformed filesystem paths reject without an uncaught
traceback. These source repairs do not establish their live deployment.

Gateway work is serialized through a bounded executor and protected by an owned
native lifetime lock. A separately locked minimal reviewer serving profile has
no legacy worker/provider graph and retains HOLD components. Full legacy provider
closure, cross-process producer ownership and server readback remain separate
open gates. Linux/Windows CI covers the native lifetime-lock boundary.

Trading repairs remove future-wide volatility normalization and same-period
signal accounting, retain large losses and initial-capital drawdown, reject
nonfinite risk inputs, cap sizing to declared risk and cash after entry costs,
and give the append-only ledger a stable projection/replay contract. Synthetic
fixtures do not establish trading alpha, realized balances or prospective
after-cost paper performance. Historical ledger bytes remain available and
require broker reconciliation before any economic restatement.

The existing portfolio audit now identifies its maturity labels as tracked-file
inventory only, with execution and customer acceptance explicitly unverified.
The priority lane points to the bounded offline forecast reviewer; historical
market-screening components remain identified as such. An infrastructure failure
detector and buyer-specific false-alert acceptance gate are not implemented by
that reviewer. The existing technical-review packet is regenerated with current
source/test identities while separately dated live observations remain dated.

The reviewer guide supplies focused trading, evidence and runtime commands plus
the full hash-locked Python 3.11.9 reproduction route. Actual source/PR/CI/release
receipts belong to the exact reviewed commit. Source merge, signed static build,
live static deployment and runtime installation are separate evidence states.
Independent evaluation, accepted buyer baseline, field benefit, revenue,
certification and valuation remain open; passing software tests do not close them.

### October 9 Wonder Studio creative-services publication

Robert explicitly requested publication of the upgraded Wonder Studio and
its business-design offer on GitHub. This scoped founder instruction extends
the existing art and presentation showcase with a supplementary creative
offer; the primary engineering validation offer and its HOLD gates remain.

The public Studio's version 15 was published from source
`c2b04f10ad1f555d1ed15d17eda66397949c94ec`. It adds a brand preview,
three fictional business demonstrations, interactive projected 3D motion,
two ten-second H.264 loops and a private custom-inquiry receipt with email
fallback. The release reported 51 passing Node checks and a successful build;
full browser visual QA was unavailable. These are first-party implementation
checks, not client results or third-party validation.

The README and existing visual-asset boundary now link to these public
experiences. This documentation change contains no private Studio source,
customer inquiries, scientific result changes or infrastructure deployment.
The separately hosted Studio release does not resolve the custom domain's
recorded release drift. Existing research, rights and production gates remain.
Price, scope, schedule and rights require agreement for each paid commission.

### October 8 founder-authorized consolidation and report repair

Active outcome 2: one external validation or paid-pilot conversion. This branch
integrates the complete histories of PRs #244, #232 and #222, resolving additive
operating-state conflicts while preserving later mainline fixes. It corrects
three newly supplied legacy report scripts in the existing research lane and
updates the existing portfolio map rather than adding a separate product packet.

The grant correction retains supplied facts, unknowns, immutable approved
snapshots and byte-consistent exports. Denominator diagnostics partition missing
inputs without double-counting overlapping exclusions. Revenue qualification now
requires explicit comparison and handling facts, rejects non-text placeholders,
excludes unknown/unbounded evidence nodes, and binds SOW prefills to the exact
qualified input and opportunity identity. Prefills remain drafts; no customer,
contract, revenue, submission or deployment is created.

Report regression tests cover nonfinite/malformed data, timestamp alignment,
undefined spectra, absent comparison versions, worse candidate loss, failed
writes and overwritten outputs. Rendering fixtures are explicitly synthetic.
The raw HyperCore histories are still unavailable; screenshot interpretation is
not a numerical rerun. Unsupported historical KPI claims are excluded from the
private business-plan revision. Public source contains no private reviewer names,
correspondence, contact records or original investor dossiers.

The existing PR consolidation map records the entire 26-PR open-queue triage.
Unintegrated conflicts, stale branches and failing dependency checks remain open;
no branch history is deleted. Production and external-validation HOLD gates remain.
Fresh test and merge receipts belong to this continuation's exact Git subject.


### October 7 technical reviewer preparation

Founder-directed repository preparation advances outcome 2: one bounded external
execution or owner-approved pilot. It updates the existing Proof Capsule verifier,
adversarial tests, schema and reviewer entrypoint; it does not create another
platform or change a frozen experiment. New regression cases reproduce malformed
Unicode crashes, invalid API resource limits and reads beyond the remaining
aggregate allowance. The verifier now rejects those inputs and bounds each read.
The existing schema, receipt version, scientific comparisons and HOLD gates remain.
The canonical technical-review packet is regenerated to bind the changed source
and test bytes. Its generation time is refreshed; its separately dated live
observations and historical receipts are preserved and explicitly distinguished.

The reviewer page now leads with GitHub source, exact runtime and hash-locked
setup, historical Git-object prerequisites, executable checks and reported skips.
It distinguishes current-source tests from the frozen computation and identifies
the October 7 live audit's 192/246 matches, 3 mismatches and 51 missing files.
The continuation incorporates the existing PDF dependency PR #210 rather than
creating a second repair: pypdf 6.19.0, verified distribution hashes and six
bounded resource/compatibility fixtures. It removes unused TensorFlow.js and
the argparse/sprintf-js/form-data closure responsible for the fresh npm audit
failure. Strict installation, peer/provenance validation and the audit threshold
remain enforced; regression checks reject root or nested reintroduction.
The local 10-package candidate graph reports zero known npm vulnerabilities.
Fresh auditing of the PDF candidate also found three urllib3 2.7.0 advisories.
The same 39-package institutional lock now uses the upstream fixed 2.8.0
release with both distribution hashes verified; its subsequent audit reports
zero known advisories. The existing dependency-security evidence lane retains
the dated comparison and outputs. Frozen research dependencies are unchanged.

The canonical reviewer guide supplies three inspection tracks, reproducible
finding fields and explicit open gates. No private reviewer identity is added.
The supplementary GitHub AI review is unavailable because account quota is
exhausted; this does not replace successful CodeQL/test receipts with a clean
AI-scan claim. Live parity, unavailable legacy feeds, guarded server recovery,
branch enforcement, provider-key closure and external evaluation remain open.
Review preparation and first-party tests do not establish independent validation,
production authorization, certification, a paid engagement or buyer acceptance.
### October 6 bounded Grant Factory draft correction

Active outcome 2 includes a separate draft correction to the existing grant
workflow. Generated narrative uses supplied project facts, marks missing facts,
preserves synthetic/unknown evidence type, and introduces no standalone software
price or deployment claim. Package checks and permitted state/kit updates retain
consistent file manifests and immutable local approved snapshots. The fictional
local rehearsal remains blocked for submission and does not establish customer
isolation, funding, accepted economics, a customer, or a software release. The
original source-to-export receipts remain unchanged. This correction is reviewable
on `codex/grant-factory-evidence-custody`; main and live deployments are unchanged.

### October 5 fixed-material and high-activity diagnostic continuation

Active outcome 2 now includes two diagnostic studies with protocols recorded locally
before their single executions, addressing specific limits of the existing evidence. These are first-party
synthetic or retrospective studies, not independent preregistration, fresh holdouts,
physical validation or authorization to promote a family or deploy a candidate.

The [fixed-volume geometry allocation study](GEOMETRY_TRANSPORT_SCREEN_2026-10-04.md#fixed-volume-cross-section-allocation-continuation)
redistributed the same conductor volume with a 10%-of-uniform cross-section floor,
fixed topology and five terminal-pair folds. All five paired held-out differences
were positive within seven layouts; the serpentine chain lost in all five folds.
Six layouts share terminal coordinates, while honeycomb and sunflower remain
separate exploratory embeddings. These results do not rank unlike embeddings.
Of 40 fits, 24 met the declared dual-gap tolerance and 16 exhausted the iteration
budget. The 4,504 training solves used about 17.40 seconds, versus 0.046 seconds
for 40 uniform-baseline evaluations: added design compute, not a speedup or energy
saving. All allocations, losses, budgets and numerical residuals are retained.
The historical 743-outage study results remain unchanged; their source binding is
preserved at public commit `6b078afb13936e388c035f4442ffaee80027ac41`.

The [high-activity interval diagnostic](../experiments/energy_multisource/stage6/high_activity_diagnostic_20261005/README.md)
tested one fixed residual-calibration overlay on the already examined 2025 record.
Only outcomes matured before each update under the stated, assumed 30-minute lag
entered calibration. Ordinary-issue intervals were unchanged. Median high-activity
coverage rose from 64.49% to 76.20%, but only one of 15 mandatory cells reached
90%; 14 still failed. Median overall interval score fell 0.675% while interval
width grew 3.289%; four cell-level score regressions remain explicit. Only 3,518
of 5,754 high-issue rows had sufficient calibration support; the remaining rows
used the unchanged baseline. These are dependent station/horizon rows, not
independent events or verified historical publication availability. Eleven new
software checks cover maturity, future-outcome isolation, fallback and identity.
No second candidate or post-result threshold adjustment was executed.

The registry validator now rejects disabled or missing promotion controls,
invalid validation-fold budgets, malformed families and duplicate/non-finite JSON.
This closes a software acceptance gap; the 26-family registry gains no performance
promotion. Physical constraints, representative external validation, the 37
unassigned prospective protocol fields and independent evaluator remain open.
Phase guidance separates a pre-run rehearsal from a post-run independent-execution
receipt and an external protocol digest; it does not fill fields or authorize a run.

### October 5 bounded test and experiment completion

Active outcome 2 includes the founder-requested completion of existing reviewer
checks and reproducible experiments. This pass fixes identified source defects and
closes finite test prerequisites; it does not finish every research family or
establish institutional certification, independent validation or production readiness.

- The [geometry transport continuation](GEOMETRY_TRANSPORT_SCREEN_2026-10-04.md)
  evaluates all 743 distinct single-edge outages in the same eight fixed-budget
  graphs. Optimized inverse updates agree with independent direct grounded solves
  within 4.88498e-15 absolute error. Surviving weights stay fixed and disconnected
  pair conductance is zero. A local median timing comparison was 0.077162 seconds
  versus 0.375205 seconds for the new direct reference, about 4.86 times faster;
  this is a host diagnostic, not physical signal efficiency or a platform speedup.
  The 26-family championship, matched hardware and physical measurements remain open.
- The existing economic-bridge producer now rejects non-finite values, invalid or
  fractional counts, wins exceeding observations, and malformed benchmark flags.
  Missing values cannot mask explicit invalid evidence. These repairs preserve
  negative research outcomes, accepted-economics holds and fictional-funds boundaries;
  they do not create trading returns, buyer savings or new observations.
- The gateway uses the supported FastAPI lifespan, preserves the same six workers
  and cooperatively cancels and awaits them at shutdown. Isolated lifecycle and
  authentication tests preserve fail-closed behavior and pass with warnings treated
  as errors. Cancellation is cooperative, not a time-bounded shutdown guarantee.
- A separate native Windows CI job runs the three existing mocked PowerShell paper
  runner fixtures using Python 3.11.9 and a hashed six-package test closure. It
  rejects skipped or empty execution and does not connect to a broker. Linux
  platform skips remain valid; native success requires the separate job receipt.
- Native C verification now enforces Zig 0.15.2 for the primary build and names a
  separate sanitizer compiler. A successful compile with sanitizer flags alone
  previously produced an unjustified AddressSanitizer claim: a deliberate heap
  overflow under the pinned Zig build exited successfully. The repaired producer
  requires named AddressSanitizer and UndefinedBehaviorSanitizer detections on
  deliberate faults, then a matching clean seven-vector result, before sealing
  its receipt. A separate hash-locked CI job rejects skipped native execution.
  This verifies host software instrumentation, not NIC/DPU hardware or expertise.

The current-main frozen EIA capsule was actually executed at
`e7e16954f27308c19f308e2e78a74eee0edb3bb0` on Ubuntu 24.04, glibc 2.39 and
Python 3.11.9 with all 18 hash-locked packages. All three suites, 31 assertions
and 28 fixtures passed. Four previously artifact-dependent checks then passed
without skips against newly generated, dated offline outputs. These outputs are
not recovered historical publication files. Capsule SHA-256 is
`900a3b66891d21216bc876efccfa21f8e8703e2b57a784eb2437d318a24bb95b`;
the frozen raw wave input remains
`8b480ec4923c17d3782eacd428ee5ea599525145ce2a0772ba934aba0a40da59`.
The separately preserved research source
`2c06c8315c667dec6bed426b533024ecb8300f59` passed 134 inherited research/custody
tests and replayed 240 interval records, 90 comparisons and 465 arrays across
187,987 dependent station/horizon targets. The numerical report exactly matches
historical payload SHA-256
`466c635a98721846e2981fd3ecfb71a5fbd093ae6c6ab46c44cd96d89e82e21f`.
All 15 selected high-activity cells still fall below nominal 90% coverage; no
fresh holdout, independent evaluator, electricity savings or geothermal benefit
is established. The prospective protocol remains unfrozen and unstarted.

The completed [PR #242 source suite](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/37340889569)
passed 1,296 tests and 87 subtests, with eight legitimate clean-checkout/platform
skips and no warnings reported. Separate exact-head jobs passed 27 native C tests
and three Windows fixtures without skips. All ten applicable maintained workflows
passed at `6cc84d78af4072700985b22a047b0c0dc9199b04`; merge
`6b078afb13936e388c035f4442ffaee80027ac41` preserved that exact tested tree.
The two subsequent diagnostic studies above retain their own protocol/source/result
identities; their integrated source checks are evidenced by the continuation PR
and exact-head handoff, not by relabeling the preceding suite. The October 5 15:35 UTC
[exact live audit](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/37333941141)
found 192 of 246 files matching, three mismatches and 51 HTTP 404 responses.
`HOLD_PUBLIC_RELEASE_PROMOTION` remains. Source/test improvements do not replace
separate exact-main deployment, signed provenance and live-byte verification.

### October 5 public art showcase and deployment boundary

Active outcome 2 includes Robert's explicit request to make the existing artwork
and presentation previews easier to share. The bounded `/art/` doorway presents
19 concept artworks, an 18-second vertical film and a ten-layout slide
preview. Native artwork detail remains 1672 × 941 pixels. Creator attribution,
rights limits and technical-evidence boundaries remain unchanged. This public
showcase does not publish an editable paid pack, private correspondence or owner
archives, and does not promise viral reach or revenue.

At Robert's request, the October 5 audio edition adds original procedural stereo
sound effects to the existing 18-second film. The video bitstream is preserved;
only the audio and media container changed. The public media manifest records the
new hash, size and audio metadata, and versioned video URLs refresh cached playback.
The 246-file release inventory is unchanged. Production deployment retains its
existing separate gates. The full media remains externally hosted in Wonder Studio.

Four small source files join the exact release allowlist, now 246 files. Artwork
and three public preview files retain absolute canonical Wonder Studio URLs;
their external bytes are not part of the repository's exact-release guarantee.
The media manifest records published preview hashes and identifies their external
hosting. Social-card editing opens the Studio, while portfolio, rights and
mathematical-observatory navigation remains local to the custom domain.

The preceding main commit `605e028226f831fba422ab0ee3ccd1d0439c9881` passed its
[full source suite](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/37243004604)
with 1,223 tests and 82 subtests passing, 8 tests skipped and 5 warnings. All 18
repository-maintained PR #239 workflows passed; the separate optional AI review
could not run because of account quota. These are first-party checks, not
institutional certification or independent validation.

The latest [exact live audit](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/37303581337)
at October 5 11:32 UTC still found 192 of the prior 242 files matching, three
mismatches and 47 HTTP 404 responses. `HOLD_PUBLIC_RELEASE_PROMOTION` remains.
A later [health probe](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/37311464748)
passed 64 observations of 16 existing contracts; it did not check the new art,
portfolio or rights routes. The 12:48 UTC
[metrics capture](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/37312141273)
observed a reachable homepage and minimal gateway, but all four legacy feeds
returned explicit HTTP 503 `operator_access_unconfigured` with unknown freshness.
Their owner-approved producer, route, schema and disposition remain the separate
[issue #234](https://github.com/robertashworth1986-debug/lumen-core-public/issues/234)
contract gap. Reachability does not establish static-release parity or data recovery.

The existing CSP allowed only same-origin image and video embeds, which would
block the Studio-hosted gallery. This reviewed source candidate adds only the
exact canonical Studio HTTPS origin to `img-src` and `media-src` in the config
and its existing repair helpers. Every other CSP directive remains unchanged;
no wildcard or script/connection permission is added. The historical August 9
security-header receipt remains immutable. Applying the new policy requires the
separate current-main security-header workflow and its explicit approval.

No production mutation is part of this source pass. Both that security-header
action and the existing exact-main static release, signed provenance/SBOM,
production environment and full live-byte verification remain required. The available connector does not expose workflow
dispatch or branch-protection writes; `main` has no enforced required contexts.
No control is weakened to resolve those capability gaps. Estate scope and external
validation remain OPEN; broader production promotion remains `HOLD`.

### October 4 current-main readiness and creator attribution

Active outcome 2 includes the founder-requested **Bounded Light Speed** naming
correction and explicit credit, **Created by Robert Ashworth using AI tools**.
Stable `/bounded-light/` URLs remain unchanged. The 19-asset creator register
records source dimensions, hashes and AI generation; it does not establish
copyright registration or exclusive rights in purely AI-generated material.
Existing repository and third-party licenses remain unchanged.

The exact-main audit at `39b20a3f3af0d8410529fd2081456575a3c04a1c` found
1,221 passing tests, 8 skipped tests, 82 passing subtests and 5 warnings in the
[authoritative full-suite run](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/37237223735).
Both CodeQL language analyses passed. These are bounded first-party checks,
not institutional certification or independent validation. The skipped checks
include four missing artifact-dependent cases, one unavailable optional Zig
toolchain case and three Windows PowerShell cases on Linux.

The same main commit did **not** pass its
[exact live-domain audit](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/37237223673):
192 of 240 files matched, three differed and 45 returned HTTP 404. The incident
receipt records SEV-2 and `HOLD_PUBLIC_RELEASE_PROMOTION`. The unmatched paths
are the old homepage/discovery files and the missing Bounded Light/portfolio
collections. New source tests cannot replace a successful exact-release and
live-byte receipt. The current source candidate adds two rights files to the
bounded allowlist, for 242 expected files at its later release commit.

A fresh GitHub branch/ruleset read found `main` unprotected, no enforced
required-status contexts, and no rulesets. No protection or permission setting
was changed. The prior PR #238 optional dynamic AI review was unavailable due
to monthly account quota; it did not produce a clean review. The current main
failure is the live-domain audit, a separate issue.

The installed connector has no workflow-dispatch operation. The prepared
production path remains the existing manual exact-main release workflow, its
literal approval input, signed provenance/SBOM, configured production gate,
rollback capture and full live verification. This update neither executes that
production action nor reclassifies production readiness. The portfolio estate
and external validation remain OPEN.


### October 4 expanded estate reconciliation — OPEN

The first portfolio edition was a selected sample. The expanded review now
contains 64 overlapping catalogue records covering all 15 configured engine
names, recovered trading and dashboard work, Grant Factory and institutional
submission stages, identity/immersive/haptics, geometry and energy research.
The [expanded scope review](LUMENCORE_ESTATE_SCOPE_REVIEW_2026-10-04.md) is the
sanitized item-level handoff for active outcome 2. It does not change the single
primary commercial offer or create 64 finished products.

Accessible Drive metadata covers 3,111 records and includes shared-reference
material with unverified ownership. Discovery counts are not owned-asset or
experiment counts. Whole-estate completion, disconnected device roots, shortcut
targets, all screenshots and larger numerical archive replay remain OPEN.

The exact research history was restored offline at `2c06c8315c667dec6bed426b533024ecb8300f59`
with 2,456 reachable commits, 1,308 tracked paths, 58 selected source/receipt
files and 24 matching artifact-integrity comparisons. No recovered project code
or scientific tests ran in this recovery. Historical Stage 6 and later assurance
receipts remain retrospective, correlated and unpromoted; their test scopes
must not be summed. The public source index now distinguishes recovered source
from remaining data replay and independent-validation gates.

EchoForm now has a privately reviewed conventional memory-boundary prototype:
32/32 authored invariants, 50/50 event handling and a deliberately wrong
upstream identity challenge failing 0/1. This does not validate harmonic identity.
LumaJet has recovered synthetic baseline source and later assurance receipts:
v1 failed its gate; v2 has a tiny internal effect with about 5.08 times baseline
planner expansions. Neither is flight or hardware validation. The canonical
portfolio map carries these corrected stages; repository-only file-presence
maturity labels do not measure privately held evidence or all historical work.

The final 64-record review-room source and public PDF are synchronized with the
sanitized Studio publication. Custom-domain deployment remains a separate,
paused exact-main signed release action. No domain login, production mutation,
external message, grant submission, legal acceptance or valuation uplift is
part of this source update.

### October 4 portfolio, registry and meeting preparation

At Robert's explicit request to organize and publish his portfolio for a
founder-reported October 5 meeting, active outcome 2 now includes an integrated
portfolio doorway and an expansion of the existing geometry registry. The
registry has 26 named candidate families across 11 lanes, preserving all 18
historical entries and negative results; none is promoted to performance-ready.
Five Platonic solids are grouped as one family. The existing four Echo Geometry
families are a conceptual taxonomy, not a physical law or performance receipt.

The June 19 registry snapshot remains immutable. The expanded catalog, artwork,
formula renderers and bounded synthetic benchmark have separate denominators
and evidence types. A screenshot, candidate name, synthetic trial, software test
and independently executed physical experiment are not interchangeable counts.
Current source preparation neither substantiates thousands of prior experiments
nor raises the existing valuation bands. The most recent located evaluation
must retain its assumptions, uncertainty and commercial-evidence gaps.

Public material uses sanitized institutional status and source-linked evidence.
Raw private emails, contact details, private agreements and private third-party
materials are excluded. The founder's public-release request authorizes this
sanitized preparation; static production still follows the exact-main signed
release workflow and configured environment gate. No external message, grant
submission, legal acceptance or runtime repair is included.

The sanitized Wonder Studio is publicly published at
`https://lumencore-wonder-studio.robertashworth4444.chatgpt.site/` and contains
the 19-artwork collection and review room. The domain homepage links to that
public Studio and its local `/portfolio/` route. The prior private-Studio
restriction below describes the earlier preparation stage and is superseded
for this sanitized collection by the founder's explicit publication request.
The custom-domain release still requires its own verified deployment receipt.
The October 4 evidence-index expansion also refreshes two dependent Argos
custody hashes. Historical evaluation dates, failed and blocked checks, and
expired action authority remain unchanged; no submission is authorized.

### October 4 Bounded Light visual collection candidate

At Robert's explicit request to continue the domain and use his wormhole and
EchoForm papers as visual inspiration, active outcome 2 includes a bounded
presentation update to the existing reviewer surface. The existing homepage
links to `/bounded-light/`: six original AI-generated concept illustrations
and an educational light-time and wave-interference lab. This extends the
visual-presentation lineage of draft PR #207 without importing that conflicted
branch or changing the sole primary buyer-owned validation offer.

Every conceptual image remains **CONCEPT ILLUSTRATION**. The lab uses declared
ideal assumptions; it is not a wormhole simulation, quantum-advantage result,
new physical theory, faster-than-light communication, or validation of the
source papers. Source papers and private Studio links are not published.
The shared static bundle introduces no login, tracking, telemetry or control
connection. Website artwork is compressed for delivery; any large-format
exports are separately labeled enlargements rather than native 16K/20K detail.

The same founder-directed collection now includes `/bounded-light/observatory/`:
an interactive geometry study with four defined families, three additional
concept artworks, a bounded point budget, shareable settings and local exports.
Trefoil tubes, projected Hopf fibers, a trigonometric gyroid approximation and
superformula shells retain their formulas and assumptions. WebGL rendering and
a Canvas fallback visualize those mathematical samples; they do not establish
physical, hardware, quantum, wormhole or performance validation. Share settings
and exports are user-operated; no account, telemetry or operator endpoint is
connected. The geometry module has numerical invariant and invalid-input tests.

This is an isolated source candidate, not a live deployment receipt. The
existing exact-main release approval, signed provenance and SBOM verification,
production-environment gate, rollback capture and exact live-byte checks remain
required. DNS, email records, VPS runtime and operator routes are unchanged.
PR #207 and deployment-control PR #208 must be reconciled by file overlap
before their later merges; neither old branch is a deployment shortcut.

### October 4 runtime follow-up

PR #235 merged as `1350a1a97ab8bc75f1c965f331905a4578092214` after all
pull-request checks passed, including CodeQL and the full repository suite.
The October 3 23:50:30–23:54:53 UTC local public sampler recorded **64/64**
successful contract observations across four rounds. These observations cover
one bounded request path and do not establish sustained uptime.

The fresh [VPS diagnostic run 37163621741](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/37163621741)
captured origin evidence at October 4 00:01–00:02 UTC and returned
**ACTION_REQUIRED: two checks passed, six failed**. Public and loopback
endpoint expectations passed. The gateway was active with no systemd restarts,
but still lacked the required explicit non-root service identity and retained a
root-owned lock. Eighteen of twenty runtime files matched current main;
`grant_application_factory.py` and `operator_api_access.py` differed. The paper
ticker was in auto-restart at 380,075 restarts; its ledger was `opc:opc:644`,
not writable by the service account, with twelve permission-error matches in
the bounded recent journal sample. These are confirmed runtime defects, not a
proven cause of the intermittent public availability reports.

Memory available was 13,064,052 KiB of 15,906,768 KiB; the OOM-kill counter since
boot was zero. Disk space was approximately 100 GiB free, with one percent
inode use. The current fixed nginx error log had no parsed records in the
requested day; the previous fixed log was unavailable. All three new journal
history queries were unavailable, so their zero signature counts are **not**
negative evidence. The follow-up collector uses explicitly UTC, space-separated
journal timestamps for older systemd compatibility and bounded error enums;
a fresh origin receipt remains the gate for confirming that collection works.

The two existing mutation paths remain
`REPAIR_PAPER_TICKER_LEDGER_OWNERSHIP` and
`REPAIR_PUBLIC_GATEWAY_DEPENDENCY_CLOSURE`. They require exact current-main
workflow dispatch and the configured private HumanUnlock secret. No restart,
runtime installation, ledger ownership change or authentication bypass was
performed by this diagnostic pass. Issue #234 remains open for the four
unmapped legacy data contracts. Public reachability, runtime integrity and
data-product availability retain separate verdicts.

### October 3 public-availability monitoring repair

Active outcome 2 includes correction of two confirmed monitoring defects, based
on main `6be9b1456472ef01e38ebe1838539297111da406`. Site Health Probe run
`37128009457` sampled the 15 contracts within four seconds; that dated green
sample did not establish continuous availability. The revised sampler records
four rounds across at least three minutes, adds the www homepage, bypasses
request caches, retains each timestamped observation and preserves failures
even when a later round recovers. Daily scheduling remains unchanged.

The metrics capture now reports homepage reachability, minimal public gateway
health, each legacy feed's response disposition and data freshness separately.
A read-only October 3 observation at 23:50–23:51 UTC found the homepage and both
minimal gateway routes healthy, while all four legacy feeds returned HTTP 503
with `operator API access unavailable`. This is a specific operator-boundary
response, not evidence that the public site was down. The source mapping and
remaining service-contract gate are in [PUBLIC_METRICS_CONTRACT.md](PUBLIC_METRICS_CONTRACT.md).
Issue #234 remains unresolved; no producer was restored and no operator route,
credential or private payload was made public.

The existing VPS diagnostic now captures bounded retained memory/OOM and
nginx/gateway/kernel history using reviewed code over SSH stdin. It emits
allowlisted counters and timestamps, explicitly reports collection limits and
does not mutate the VPS. Its push-main run provides a new opportunity to collect
origin evidence. Neither source repair nor a successful current HTTP request
establishes the cause or durable resolution of the reported intermittent
failures. Existing release, authentication and production controls remain in
force; this pass does not authorize a blind restart or redeployment.

The seven focused health, metrics, operator-access and diagnostic modules pass
99 local tests plus 37 subtests on Python 3.12 / pytest 9.1.0. The collector's
regressions include request-controlled filenames that must not become outage
signatures. This local result is not an exact-commit full-suite CI receipt or a
production recovery receipt.

### September 25 live-loop integrity repairs

Active outcome 2 includes a bounded repair of the existing source-to-evidence
path, based on main commit `dfc45fe2a05102c835dafe05d9b847cd04566086`.
The API source monitor now accepts the checked-in registry and provider-config
shapes, rejects ambiguous inputs, and requires an explicit successful probe
with a valid, non-future timestamp inside the accepted age limit before showing
ACTIVE. Credential presence remains a separate diagnostic. The report itself
does not perform network probes or establish dataset readiness.

The canonical government collector now preserves direct collection failures;
historical registry records cannot replace them or increase current successful
source and row counts. Metadata, content items and output-field counts remain
separate from data rows. Diagnostic credential assignments are redacted by
removing their values. The public live-breadth manifest separately checks probe
and dataset snapshot observation age, with finite positive age thresholds;
missing, stale or future snapshot timestamps cannot become review-ready.

Seven focused modules passed **134 local tests** on Python 3.12.14 / pytest
9.1.1. This is not a full-suite or exact-commit CI pass. The
[bounded review receipt](evidence/live_loop_integrity_review_20260925.md)
records the command, source identities, covered failures and remaining gates.
No provider collection, current availability measurement, new performance
experiment, frozen-delta promotion, production deployment or external
validation occurred in this repair pass. Existing frozen EIA evidence remains
unchanged and on HOLD. The next operating gate remains a permissioned,
timestamped source snapshot followed by the accepted comparison protocol and
human review; code repair alone does not prove continuous operation or savings.
### September 24 sector coverage diagnostic

Active outcome 2 now includes a source-level extension of the existing offline
denominator audit for grid, marine and geothermal research. Each scheduled
target excluded from a comparison is attributed to its complete missing-input
pattern; overlapping marginal counts are explicitly separated from exclusive
lost-target totals. This makes the next source-repair work more precise without
changing forecasts, thresholds, frozen results or research-only decisions.
The [existing assurance note](DENOMINATOR_AND_PAPER_ASSURANCE_2026-09-11.md)
records 81 passing focused local tests and both intact EIA packet identities.
No complete-suite CI pass, rescored historical packet, improved coverage,
independent validation, deployment or external action is established by this
source change. Buyer-owned scope, chronology and prospective capture remain
the next validation gates.

### September 21 live-release audit hardening

Active outcome 2 now includes a bounded correction to the existing exact-byte
audit: an empty manifest cannot produce a passing release receipt, all rows are
validated before HTTP requests, and manifest inputs and response bodies have
explicit size limits. Both the live verifier and incident classifier require
the declared byte count to match in addition to SHA-256. Oversized and
interrupted responses remain visible failures. The existing signed release,
human approval, installation, rollback and trading boundaries are unchanged.

The focused local release, incident, supply-chain, historical-receipt,
repository-security and institutional-crosswalk suite passed 167 tests and
eight subtests on Python 3.12; three existing root-incompatible POSIX installation
tests were skipped. This is not a complete-suite pass. The existing hash-locked
Python 3.11.9 CI remains the authoritative complete-suite gate for the eventual
reviewed commit.

A fresh September 21 read-only GitHub branch observation at main commit
`01edc688003e3e22387cd78d7db4715b0f75f675` still reported `protected=false`,
required-status enforcement `off`, and no required checks. This is an open
repository-setting gap; no setting was changed. No certification, independent
security review, historical credential revocation or broader production
authorization is established by the source correction or local tests.

The follow-up evidence review also reproduced an empty-manifest acceptance in
the new frozen replay runner's generic check. The original runner and manifest
bytes remain immutable. The dedicated `VERIFY_EIA_CONSTRAINT_REVIEW.py` now
supersedes that check with reviewed digest pins, exact required membership,
strict schemas and contained paths. Seventeen adversarial tests and both retained
packets pass. This establishes bounded first-party integrity only.

### September 21 frozen constraint replay

Active outcome 2 now includes a retained replay of the unchanged July EIA
residual protocol. The review plan and runner were committed before execution;
all seven development candidates, six holdout baselines and original failed
gates remain visible. On 1,176 identical authority-days, the selected residual
candidate reduced descriptive MAE from 36,568.783 to 15,979.087 MWh (56.304%)
versus EIA's archival DF series; WAPE was 3.53355% versus 1.54402%. This is an
actual historical candidate-versus-comparator comparison. EIA permits forecast
scope to differ from physical demand, so DF is not an established matched
operational incumbent. The reduction versus the strongest aggregate algorithmic
baseline, direct LightGBM, is 10.602% MAE.

Promotion remains HOLD: four authorities fail the 150-day minimum, and SWPP's
0.074058 seasonal-MASE regression against autoregressive ridge exceeds 0.05.
The panel was already inspected; the new run is reproduction, not a fresh
untouched or prospective holdout. As-of data availability, independent replay,
a buyer action/cost function and operating savings remain unestablished. No
sector-dollar extrapolation or production authority follows from forecast-error
reduction. The existing [CODECHECK note](CODECHECK_EIA_EXECUTABLE_COMPUTATION_NOTE_2026-07-20.md)
contains full comparisons and the hash-verifiable input/code/output receipt.

A fixed-model later-archive test on July 13–September 8 also reduced MAE by
18.509% versus the same direct LightGBM baseline. Only 285 of 464 possible
authority-days survive (61.42%); SWPP has zero eligible rows and its original
regression remains unresolved. The model was not refitted on 2026 labels and
all six comparators remain visible. This additional retrospective test fails
the original coverage gates and establishes no matched operational baseline,
prospective forecast, independent validation or operating savings.

### September 21 portfolio and review-path update

At the founder's request, the canonical homepage, README, investor brief and
reviewer start page now show the wider LumenCore engineering portfolio. The
existing `docs/PLATFORM_PROOF_AND_COMMERCIALIZATION_MAP.md` is the portfolio
source map, with asset-specific implementation, research, simulation and concept
states. This work supports active outcome 2 and retains the buyer-owned baseline
validation sprint as the primary commercial entry point.

The public story now includes the trading/exchange architecture, Grant Factory,
Mission Control, Quant Lab, ProofLock, utility/geothermal and thermal research,
HyperCore, EchoLock, LumaJet, the LumaSkin virtual engineering lab, digital-twin
concepts and Node-RED/immersive prototypes. Historical transaction evidence is
recognized without asserting strategy-attributed net profit. Virtual engineering
receipts are not physical or human validation. Science-museum work is a possible
application, not a verified counterparty deployment. Founder-held evidence is
identified separately from public source artifacts.

The shared navigation now compares normalized complete paths; the homepage no
longer marks nested Evidence and ProofLock routes active. The public reviewer
docket points to the portfolio map while preserving every unestablished claim
gate as false. The legacy operator routes remain noindex HOLD stubs, and no live
order, hardware, data-rights or public-sector certification authority changes.

This source update is not a production deployment receipt. Release identity,
attestation verification, bounded installation, rollback capture and live-byte
verification remain separate requirements of the guarded static-site workflow.

### September 21 production release preflight

Active outcome 2 now has a stricter static-release workflow: production access
requires an explicitly approved exact main commit and successful verification
of both GitHub signed provenance and SBOM attestations for the rebuilt archive.
The source change adds no deployment, runtime repair, DNS change, or broader
platform production approval. The September 20 main audit for `ea842a2` matched
188 of 189 files and held the release because `operator_home.html` differed;
that dated observation requires a fresh audit after any approved deployment.

### September 20 reviewer-surface update

The canonical homepage, repository introduction, investor brief, and reviewer
start page have been refreshed as one evidence-led review path for EC mentors,
technical reviewers, and prospective buyers. The former trading-led investor
brief is superseded; its valuation ranges and broad production-readiness claims
are not current company claims. The review path uses source-linked, dated
first-party receipts and exposes the remaining independent-execution,
buyer-acceptance, and production-authorization gates.

This is a presentation and navigation update supporting active outcome 2. It
does not create another product, validation package, external-review result,
customer relationship, or outreach authorization. Public-site deployment is a
separate exact-snapshot action under the existing guarded release workflow;
this source update is not a live deployment receipt. The August operating and
runtime observations below remain dated historical observations.

### Company scope

LumenCore helps a buyer or technical reviewer compare an AI, forecasting, routing, or infrastructure candidate against an accepted baseline under predeclared rules, then packages the result, failures, provenance, and claim boundary into a hash-verifiable decision record.

## Active outcomes

### 1. EPRI / Open Power AI Consortium onboarding

**State:** Consortium onboarding is active under a private controlling agreement. Exact agreement status, dates, named-party terms, IP terms, and publicity terms remain in the private legal record. This lane is not funding, an award, an endorsement, independent validation, or permission to make broader public claims.

**Existing asset:** The private agreement and existing Gmail thread are the controlling records. The July 29 reply supplied two harmonic-ring files that the founder identified on August 8 as the wrong consortium mark. The founder-confirmed replacement is `assets/brand/lumaarc_arc_seal_v1.png`, SHA-256 `1ed1c9b00e273aa9e781bd7fd0a4fcc3fc542257c6d294c8e8fbfada500701af`. LumenCore remains the member and company name; LumaArc is the seal name, not a company rename. On August 8, one corrective reply was sent in the existing thread with that exact asset attached and instructions to disregard the two July 29 files; Gmail sent-message ID `19fe0959c4875700` is the transmission receipt. On August 4, EPRI/OPAI replied that no extra contribution packet is required and that Robert's presence and contributions to Member Representative Committee and Work Group meetings are enough; optional thoughts or suggestions can be shared during those calls.

**Next allowed action:** Return to the no-duplicate hold. Attend the recurring Member Representative Committee and selected Work Group meetings, review public/non-proprietary materials, and share bounded thoughts during those calls when useful. Keep IP and publicity actions separately agreement-gated; do not send another logo correction, onboarding acknowledgment, or contribution-path follow-up unless EPRI/OPAI asks.

### 2. One external validation or paid-pilot conversion

**September 28 Revenue Engine import repair:** The existing PR #222 test
modules now load the three revenue scripts by exact repository path, following
the existing test convention. This removes their collision with Python's
standard-library `code` module without making the source directory a package,
changing the revenue behavior, or altering frozen evidence. The original
collection error was reproduced before the correction. On local Python
3.12.14 with pytest 9.1.0, all seven existing revenue tests passed with the
standard-library `code` module already loaded; its module identity remained
unchanged. Repository-wide collection reached 826 tests, including all seven
revenue tests, but remained blocked by 11 unrelated import errors for missing
local NumPy, pandas, Requests, FastAPI and PyYAML dependencies. This is a
bounded local repair, not a full-suite pass. The hash-locked Python 3.11.9 CI
suite remains the authoritative merge gate. No deployment, external action,
buyer acceptance, revenue or validation is established.

**Reviewer doorway:** PR #66 was merged on July 23 at `aed61134407426114148e3201cd357099d155864`. It is the canonical human-and-machine evidence-navigation layer. PR #74 is the current merged CODECHECK/reviewer package. Route a qualified non-author evaluator through those existing surfaces; do not create another platform or validation package.

**Private external-review follow-up:** After a private technical review, a prospective collaborator shared private product documentation, requested LumenCore's thoughts, and proposed another discussion. Keep the counterparty identity and materials out of the public repository. This is not a partnership, customer, paid pilot, endorsement, validation, or permission to publish the material. Reduce any follow-up to one buyer-owned workflow, baseline, metric, data-rights boundary, and go/no-go decision.

**Agent Arena sub-harness:** PR #94 merged the single canonical V5 adversarial multi-agent synthetic/replay harness into `main`. It tests seven specialist roles under corrupted telemetry, hidden faults, role dropout, Byzantine proposals, predeclared selection-versus-holdout separation, deterministic robustness statistics, and hash-bound custody. The frozen reference scenario uses six selection floors, two holdout bosses, eight selection seeds, eight disjoint holdout seeds, and a no-red-team ablation. It is a secondary stress/holdout harness inside the proof-to-pilot architecture, not a separate product or a replacement for the PR #74 independent-execution target. Positive results remain synthetic/model evidence until a qualified non-author independently executes the frozen harness or a buyer supplies an accepted dataset or simulator, baseline, metric, threshold, and failure rules.

**LANL VISION:** A bounded non-proprietary follow-up package was sent after the July 16 meeting connection was not completed. Wait for a reschedule, a specific information request, an agreement-path owner, or a no-fit decision.

**EVTit / Vynetic:** Two near-duplicate follow-ups were sent in the same thread. The lane is locked. Wait for a substantive reply; do not send another update, deck, or scope packet.

**Selection rule:** The first qualified party that agrees to a controlled dataset, incumbent baseline, prelocked metric and threshold, reporting format, failure rules, and one go/no-go decision becomes the single active external-validation lane. All other pilot outreach pauses.

### Public runtime incident and recovery boundary

**Latest verified point-in-time observation (August 10):** The committed
`data/site_health.json` snapshot at `2026-08-10T12:33:26Z` recorded all eight
monitored endpoint checks operational: six static HTTP checks and two dynamic
JSON-contract checks. A separate read-only probe beginning at
`2026-08-10T13:50:06Z`
matched the declared content contracts for the five current bounded reviewer
surfaces and the two minimal public gateway endpoints, `/health` and
`/api/public/status`, with HTTP 200 responses. These observations establish
point-in-time public liveness only. They do not establish the recovery cause,
that the guarded dependency-closure repair ran, the deployed gateway commit or
source closure, sustained availability, production approval, or external
validation. Those liveness observations are not exact-byte release parity;
the later separately gated static-release receipts establish that narrower
condition for named release `1ce7c359`.

**Reconciled named static release (August 12):** PR #167 merged the exact
43-file release-control update at commit
`1ce7c35975a4011fa844e8b39ccbc950c8c0f398`. Main-branch supply-chain run
`31548604617`, separately human-gated deployment run `31548829514`, and
read-only post-deployment audit run `31548906293` all completed successfully.
The deployment captured rollback state and the deployment and audit receipts
each recorded 43-of-43 exact live-byte matches with `release_verified: true`.
The audit classified `NO_INCIDENT_OBSERVED`, severity `NONE`, decision
`MONITOR`. PR #168 then merged the append-only receipt history at commit
`5e03e6c98e67d9f8c68ae6816d2c56a9f2cd301d`; the retained verifier
reconstructs both named deployed Git subjects. These are first-party static
release and custody results. They do not establish external validation,
certification, whole-VPS or gateway provenance, scientific validity, customer
acceptance, revenue, savings, or broader platform production authorization.
Neither gateway liveness nor exact-byte deployment constitutes external
validation.
Later commits that do not change the allowlisted static bytes do not replace
the named `1ce7c359` deployment identity.

**Scheduled health-writer integrity receipt (August 12):** PR #171 merged the
exact tested head `600b138f1008022b6c5bb07695eb8c55d3aa3b2b` at merge commit
`f2ea3a3bffbf344b7fa007c222b56f7d7e5bb5c1`. The change requires the daily
health workflow to validate the complete 15-endpoint snapshot and badge
contracts; permits repository mutation only for `data/site_health.json` and
`data/uptime_badge.json` using null-delimited Git path handling; rechecks the
committed path set after rebase; and verifies the exact remote branch head
after publication. The clean local repository suite recorded 798 passed tests,
7 skipped tests, and 48 passed subtests. The PR's gateway-contract, engine,
institutional-readiness, dependency-review, repository-trust, and both
language-specific CodeQL checks passed on that exact head. Manual post-merge
health run `31559056763` then completed successfully, created snapshot commit
`b1fa45003746a9b4b6c3b033034182d97ace3ac0`, and recorded 15-of-15 declared
contracts healthy at `2026-08-12T03:07:11Z`; Pages run `31559066395` deployed
that snapshot successfully. This is first-party software, publication-integrity,
and point-in-time liveness evidence. It does not establish sustained uptime,
gateway source closure, penetration-test or security certification, external
validation, scientific superiority, profitable trading, customer acceptance,
revenue, savings, or broader production authorization.

**Current read-only VPS runtime verdict (August 12):** PR #181 merged the
guarded gateway runtime-closure repair at exact merge commit
`40a0463e061e912263a62527fdab2c0fbb92c6d2`. After PR #183 merged the exact
repository-security state, read-only diagnostic run
[`31573034746`](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/31573034746)
captured a complete bounded receipt against current `main` commit
`6a22b2f748ecb2457d89a0494d0c04f4374a93b9` at `2026-08-12T07:13:07Z`.
The diagnostic workflow completed because the receipt was captured; the
separate commit status correctly reported failure with verdict
`ACTION_REQUIRED`. Its assessment recorded one passing check, six failing
checks, and zero unknown checks. The raw diagnostic SHA-256 is
`340b26868946b02a9516e91c717acff3c46e879b45cf40d7a379c2239a1ab412`.

All seven declared public/loopback endpoint codes passed, including the
expected fail-closed HTTP 503 at the unauthenticated protected snapshot route.
The gateway was active and its lock PID matched the systemd main PID, but the
effective unit still had no explicit `User` or `Group` and the live lock was
`root:root:644`. The approved 20-file current-main gateway closure recorded 19
matches, one mismatch (`grant_application_factory.py`), and zero missing,
symbolic, or unreadable targets. The paper-ticker process was in `activating`
and `auto-restart` with `NRestarts=193976` under `lumencore:lumencore`; its exact
empty ledger remained `opc:opc:644`, was not writable by `lumencore`, and
produced twelve allowlisted `PermissionError` observations during the bounded
five-minute window. The same receipt recorded a successful read-only `nginx -t`.
Capacity was not the cause: about 108 GiB remained available and inode use was
one percent. The retained artifact is `lumencore-vps-runtime-31573034746`,
artifact ID `9132068760`, with GitHub
artifact digest
`sha256:776578b53ed73d95d1fc1e74f7a6335a5cb36bc0edd702fe1add688a6cf3ae2e`
and seven-day retention.

The existing manual gateway repair now treats source and service identity as
one hash-bound runtime closure under the unchanged exact approval phrase
`REPAIR_PUBLIC_GATEWAY_DEPENDENCY_CLOSURE`. It validates a deterministic
systemd drop-in, migrates only `/opt/lumencore/run` to
`lumencore:lumencore:750`, requires the live PID lock to become
`lumencore:lumencore:640`, applies the 20 exact source files, and restores the
prior source bytes, service drop-in, run-directory metadata, and active/stopped
service state if any identity, parity, or HTTP contract fails. The distinct
paper control remains `REPAIR_PAPER_TICKER_LEDGER_OWNERSHIP`.

The private `LUMA_HUMAN_UNLOCK_TOKEN` repository secret remains unconfigured,
so neither repair was dispatched and no VPS mutation was attempted. A fresh,
target-specific founder authorization and that private HumanUnlock control are
required before either workflow can change production. These first-party
observations prove only current bounded liveness, runtime identity, source
drift, capacity, and the named paper-worker failure. They do not establish
sustained availability, whole-VPS parity, external validation, profitable
trading, customer acceptance, revenue, savings, or broader production
authorization.

**Repository vulnerability closure (August 12):** Dependabot alert #3,
`GHSA-5239-wwwm-4pmq`, identified a low-severity local-access ReDoS advisory in
the security-header workflow's Pygments dependency. PR #162 upgraded the
hash-locked requirement from 2.19.2 to patched release 2.20.0 and merged at
`d3a6ecd78159c7dd418b1f870bf160c931a77f30`. The dependency-graph update and
security-header receipt workflow passed, and GitHub recorded the alert as
`fixed` at `2026-08-12T00:31:24Z`. This closes that named alert only; it does
not establish a vulnerability-free codebase, penetration test, runtime scan,
or external security certification.

PR #175 separately upgraded the institutional Requests pin and complete
hash-locked closure from 2.32.5 to 2.33.0 for `CVE-2026-25645`, repaired the
pin-drift mutation test so it follows the current manifest rather than a
hard-coded version, and merged at
`8f9fe26d031ff1ad2eed834a2a70fa8aa2015305`. The exact repaired head passed
dependency review, both CodeQL language analyses, the focused institutional
verifier, and the complete repository suite; the same complete and focused
gates passed after merge on `main`. After the dependency graph refreshed,
GitHub reported zero open Dependabot alerts at the point-in-time check. This
closes the named Requests advisory and current GitHub alert queue only; it does
not establish zero vulnerabilities, a penetration test, dependency freshness
outside the tracked manifests, or external security certification.

On August 8, read-only current-state probes established that DNS, TLS, nginx,
the static reviewer surface, VPS storage, and filesystem inodes were available,
while the dynamic gateway returned HTTP 502 and had no listener on loopback port
8787. The storage diagnostic recorded about 109 GiB free and no inode pressure,
so capacity was ruled out as the cause.

PRs #114, #115, and #116 progressively hardened the existing read-only VPS
diagnostic. The post-merge runs `31246089227`, `31246224480`, and
`31246373528` established a restart storm, a dead-PID singleton lock, and the
allowlisted failure signature `ModuleNotFoundError: No module named
'booth_public_contract'`. The deployed gateway source was a stale monolithic
file; the reviewed `main` entrypoint is a fail-closed facade whose local import
closure was not deployed. This is deployment drift and an incomplete runtime
bundle, not evidence of a storage failure or a defect in nginx routing.

The repository now contains a deterministic gateway-closure repair path. It is
inspect-only by default, binds twenty explicit local Python files to one bundle
SHA-256 and a full current-main commit, validates the staged entrypoint and live
order block before installation, refuses symbolic targets, removes only a
verified dead-PID gateway lock, restarts only `luma-gateway`, validates minimal
public health/status contracts, and rolls back every affected file on failure.
The corresponding workflow is manual-only and requires both the exact phrase
`REPAIR_PUBLIC_GATEWAY_DEPENDENCY_CLOSURE` and the private HumanUnlock secret.
The private value is transferred as an owner-only file and is never expanded
into the remote command line; apply mode refuses any target, service, lock,
runtime, or probe identity outside the exact production contract. Recursive
temporary cleanup is path-bounded, and every workflow dependency is pinned to
an immutable commit. The evidence recorded here does not establish that this
guarded repair was dispatched or that it caused the later point-in-time
recovery. The separate public-static-site release gate remains unchanged and
cannot authorize gateway repair.

The public health contract is intentionally minimal: it reports liveness,
service identity, the operator-access boundary, and a UTC timestamp, but no
process IDs, internal artifact freshness, service inventory, or operator data.
Detailed health remains available only at the token-protected
`/api/operator/health` route.
The daily health workflow classifies the static reviewer surface and dynamic
gateway independently; a healthy static page can no longer conceal a failed
control plane.

The reviewed public browser contract is now separated from the operator
runtime contract. Public pages request only `/health` and
`/api/public/status`, validate the fixed minimal response fields, and display
gateway liveness without probing `/api/snapshot` or inferring execution state.
The canonical homepage no longer links directly into the no-index operator
mission surface. Operator pages retain their separate protected runtime path.
That repository change alone did not establish live gateway health. The August
9 public probes are separate point-in-time liveness evidence, not proof of the
recovery mechanism, the deployed gateway commit, sustained service health, or
static exact-snapshot parity.

Manual gateway-repair run `31248779848` accepted the exact current-main commit
and exact approval phrase, then failed closed before SSH because repository
secret `LUMA_HUMAN_UNLOCK_TOKEN` was not configured. No VPS change was
attempted. The paper-ticker repair was not dispatched because it depends on the
same missing private action-time control. Both workflows now emit a specific
non-secret error for this precondition while retaining the existing gate.

PR #125 corrected the read-only loopback probe so it preserves the public TLS
hostname while pinning the connection to `127.0.0.1`. Post-merge run
[`31251081800`](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/31251081800)
then established the complete request path without disabling certificate
validation: nginx itself returned HTTP 200 on loopback, the gateway route
through nginx returned HTTP 502, and the direct gateway port refused the
connection. The public root, opportunity-sprint page, and nginx health surface
returned HTTP 200 in the same observation window. This isolates the outage
behind nginx rather than at DNS, TLS, or the static web tier.

PR #126 bound the runtime diagnostic to the exact `main` commit and compared
the deterministic twenty-file gateway source closure with the deployed VPS by
path and SHA-256 without reading or publishing file contents. Post-merge run
[`31251277886`](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/31251277886)
recorded source commit `4348ff77ef5731221c7116dfa7674b4feda63803`,
approved bundle SHA-256
`af63196219884e7c8d122231dc1aa6e7a919018778082ed0ff4794919ea51c05`,
zero matching files, sixteen mismatched files, and four missing files. The
missing files were `booth_public_contract.py`,
`execution/order_safety_gate.py`, `luma_experience_gateway_legacy.py`, and
`operator_api_access.py`; no symbolic or unreadable targets were found. This
proves whole-closure deployment drift, not a one-file patch condition. It does
not prove that the guarded repair has run or that the live gateway is healthy.

Manual health run `31247095241` recorded the first current-contract snapshot at
commit `0ff614be`: all six static reviewer endpoints passed, while both dynamic
gateway contracts returned HTTP 502, so the public state is explicitly
`degraded`, with `static_surface_state=operational` and
`dynamic_gateway_state=outage`.

Read-only runtime run `31247114240` also showed two worker restart histories
that require diagnosis before any service change: `luma-paper-ticker` was in
`auto-restart` with `NRestarts=179423`, and `luma-symbol-awareness` was running
with `NRestarts=205076`. These counts do not establish a current root cause or
performance defect by themselves. The bounded VPS diagnostic now captures only
allowlisted, redacted failure signatures from five-minute windows for those two
workers, alongside the existing two-minute gateway window. It remains
observation-only: no restart, stop, deletion, log vacuum, or configuration
change is permitted by that workflow.

Post-merge diagnostic run `31247338156` isolated the paper ticker's current
failure signature to `PermissionError` while opening
`/opt/lumencore/out/execution/multi_exchange_paper_ticker_ledger.jsonl`. The
same bounded run found no allowlisted symbol-awareness failure in its five-
minute window. Follow-up read-only run `31247505265` proved that the stack root
was traversable and both output parents were `lumencore:lumencore` mode `755`
and writable, while the exact zero-byte ledger was `opc:opc` mode `644` and not
writable by `lumencore`. No symbolic path was present. This identifies the
current paper-ticker crash cause without reading ledger contents.

The repository now contains a manual-only, rollback-capable repair for that
exact incident. It binds the empty-ledger SHA-256, `opc:opc:644` pre-state, one
repair-script SHA-256, and a full current-main commit; requires both the exact
phrase `REPAIR_PAPER_TICKER_LEDGER_OWNERSHIP` and the private HumanUnlock; stops
and starts only `luma-paper-ticker`; changes only the exact ledger to
`lumencore:lumencore:640`; and installs one bounded restart-policy drop-in. It
refuses symlinks, multiple hard links, path or metadata drift, an unexpected
service identity, or a missing paper-only preflight, and rolls the metadata and
drop-in back if service stability fails. The repair has not been dispatched in
this recorded state. Future full deployments explicitly preserve the ledger,
set least-privilege ownership/mode, and bound both paper-ticker and shadow
symbol-awareness restart storms.

### Institutional full-suite gate receipt — August 12, 2026

PR #174 merged the repository-wide institutional test gate into `main` at
commit `852dd05f7320705e764f0cd488e874248ae57b36`. Every pull request and every
push to `main` now runs the complete first-party pytest collection on Ubuntu
24.04 with exact Python 3.11.9, a hash-locked binary-only dependency closure,
`pip check`, a source-mutation check, and a commit-bound JUnit artifact. The
fast focused readiness verifier remains a separate job.

The first PR attempt was blocked before merge because GitHub dependency review
identified two high-severity malformed-PDF infinite-loop advisories in
`pypdf==6.13.2` (`GHSA-5xf7-4p34-54qr` and
`GHSA-g867-7843-wf8q`). The final reviewed head upgraded the direct pin to
`pypdf==6.15.0`, regenerated the complete lock, and then passed dependency
review. This is evidence that the security gate rejected one vulnerable
dependency change and that the corrected closure passed that bounded review;
it is not a whole-system or future vulnerability-free claim.

Post-merge institutional-readiness run
[`31563059423`](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/31563059423)
executed against the exact published `main` commit and recorded:

- dependency-lock status `INSTITUTIONAL_DEPENDENCY_LOCK_VALID`;
- 14 direct pins, 39 resolved packages, and 717 recorded SHA-256 hashes;
- normalized lock SHA-256
  `90cc18300371fcb3a09f3967c15880b97ddad174ec7f10e91d1f8bba5d715229`;
- `pip check`: no broken requirements;
- 802 passed tests, 7 explicit skips, 5 warnings, and 48 passed subtests in
  46.87 seconds; and
- successful source-mutation rejection and artifact upload steps.

The main-bound JUnit artifact is
`institutional-full-suite-852dd05f7320705e764f0cd488e874248ae57b36`,
artifact ID `9128457813`, with GitHub artifact digest
`sha256:de02d797e0c28c5c6f90c877ee43dd0a73053294f6db1450e41b73ff1e079115`.
It expires under the workflow's 30-day retention policy on September 11, 2026.

The seven Ubuntu skips are not counted as passes: four require generated
publication or evidence artifacts absent from a clean source checkout, and
three require Windows PowerShell rather than the Ubuntu runner. A complementary
Windows run on the reviewed head recorded 802 passed, 7 skipped, 5 warnings,
and 48 passed subtests in 411.82 seconds; its three platform skips were the
POSIX-only root-side Bash integrations. Together these runs establish bounded
cross-platform first-party software behavior for the tested source. They do
not establish production readiness, independent or field validation,
certification, zero vulnerabilities, revenue, savings, profitable trading, or
sustained uptime.

### Receipt reconciliation

| Lane | Verified state | Next action |
|---|---|---|
| Army AIDP Draft CfS 2 | ACC-APG confirmed receipt on July 14. | Wait for a substantive request; do not ask for another receipt. |
| Air Force `SAF-AQ-RFI-26-0001` | The Air Force confirmed receipt on July 13. | Wait for a substantive request; do not ask for another receipt. |
| CDC `75D301-26-RFI-73483` | CDC confirmed receipt and said it would follow up. | Wait. |
| DARPA DICE proposal abstract | The IPTO submission-finalization confirmation establishes receipt. | Inspect BAAT or new inbound status; do not send the stray Gmail draft or a duplicate abstract. |
| DARPA `SN-26-97` | The package was sent after DARPA confirmed that compliant submissions were welcome. | Wait for substantive contact; do not send the existing reply draft. |
| DLA MissionWeave `DLA26BZ03-NV011` | DLA SBIR/STTR Program Operations confirmed on July 28 that DSIP showed the proposal as `In Progress`, so it was not formally submitted. The July 22 noon ET deadline passed. | Preserve the packet. Do not claim submission or send another status request without a new official ask. |
| Navy HarborSentinel `DON26BZ03-NV063` | No final-submission receipt was found. The July 22 noon ET deadline passed. | Preserve the packet. Do not claim submission or start late-submission outreach. |
| HHS Project Argos `ONC-ARGOS-SSN-2026-OS351107` | Exactly one response email was transmitted before the July 30 deadline. An automatic out-of-office reply proves mailbox-system reach only; formal receipt and agency review are not confirmed. | Do not resend. Wait for a substantive HHS request; do not claim receipt, review, selection, award, funding, or validation. |
| EPRI / Open Power AI Consortium | The MOU was completed by all parties; LumenCore provided its primary contact and initial Work Group representatives and received the recurring Member Representative Committee invitation. The founder identified the two July 29 harmonic-ring logo attachments as the wrong consortium mark. One corrective reply was sent August 8 in the existing thread with the founder-confirmed LumaArc seal attached and a statement that the member/company name remains LumenCore; Gmail sent-message ID `19fe0959c4875700` is the transmission receipt. EPRI/OPAI replied August 4 that no extra contribution packet is required and that presence and contributions to MRC and Work Group meetings are enough. | Return to the no-duplicate hold and attend meetings. Do not send another logo correction or onboarding follow-up unless EPRI/OPAI asks. These records support onboarding and bounded meeting participation only, not endorsement, independent validation, an award, funding, broader licensing, utility adoption, approval of a specific claim, or performance. |
| Nashville EC Fall 2026 TakeOff | EC confirmed receipt of the authorization, electronic signature, and onboarding responses; confirmed everything was received on time; and said the materials would be included with the onboarding submission. EC said Robert is all set for now unless it needs something further. | Do not resend or send another acknowledgment. This confirms timely onboarding-material receipt only. It does not establish payment, a secured spot, program completion, a contract, endorsement, or validation. The separate $125 deposit remains founder-controlled and is due August 14. |
| Launch Tennessee SBIR/STTR support | Exactly one request for no-cost application support and information about the consultant microgrant was sent July 30. No reply was found. | Wait. Do not treat the request as funding, an award, eligibility confirmation, acceptance, or validation, and do not create a duplicate campaign. |

A receipt proves delivery only. It does not prove selection, technical validation, award, contract, deployment, or government endorsement.

### 3. Patent official-record protection

**Keep:** The Patent Examination Review Matrix, customer-number association draft, reviewer handoff, hash-verified patent vault, and official-record retrieval checklist.

**Do next:** Retrieve and review every official Patent Center notice, filing receipt, application document, missing-parts notice, and deadline for application 19/281,546.

**Do not do:** Create more public patent narratives, solicit broad technical endorsements, sign or submit the association form, pay a fee, or infer that outside review can cure missing as-filed support.

## Curated Codex package inventory

### Canonical and active

| Package | Decision |
|---|---|
| `QUICKSTART.md`, Proof Capsule verifier, public EIA/DICE capsule, and focused CI | **Canonical product surface. Keep and maintain.** |
| External evaluator acceptance handoff and portable validation docket | **Keep as the controlled outside-review protocol.** |
| Agent Arena adversarial multi-agent harness | **Keep as a bounded synthetic/replay sub-harness for agentic validation; V5 is the single canonical Arena configuration; do not promote it as a separate platform or as external proof.** |
| Patent Examination Review Matrix and customer-number association draft | **Keep in the protected patent lane. No public expansion.** |
| CDC AI Acquisition RFI package and artifact manifest | **Submitted; receipt confirmed. Freeze and wait.** |
| LANL VISION follow-up package | **Sent; freeze and wait.** |
| Live Funding Portal Handoff | **Use only as a deadline queue. Update existing rows; do not create parallel trackers.** |

### Preserved research, not active product scope

| Package or PR | Decision |
|---|---|
| OPAI crawlers and consortium intelligence engines | Preserve branch history; extract only the outreach lock and public facts needed for onboarding. |
| Alpha Intelligence Champion | Freeze as research. |
| Hybrid Echo Routing evolution lineage | Freeze as research. |
| QMPL and adaptive swarm sweep | Freeze as research. |
| Architecture discovery and validation engine | Freeze; it inventories scope but does not become another product. |
| Geometry publication packet, DICE/geometry audit, HarborSentinel, NV065 sensor tasking | Preserve as bounded research evidence; keep outside v1.0. |
| Trading engines and live execution surfaces | Safety-maintenance only; no product promotion and no live orders. |

## Pull-request curation

- **PR #34** — merged Proof Capsule v2 assurance foundation.
- **PR #57** — merged public-copy correction; wording cleanup is not technical validation.
- **PR #66** — merged canonical reviewer and agent doorway; exact-head evidence-graph and order-safety gates passed.
- **PR #74** — merged externally executable EIA/CODECHECK reviewer package; no independent execution receipt is present.
- **PR #94** — merged Agent Arena V5 synthetic/replay stress and holdout harness; it does not establish field or external validation.
- **PR #162** — merged the hash-locked Pygments 2.20.0 security update at `d3a6ecd7`; Dependabot alert #3 is fixed, not a whole-system security claim.
- **PR #164** — merged eight noindex HOLD stubs at `f7662d5`; those files are included in named release `1ce7c359` and its 43-of-43 live receipt.
- **PR #167** — merged the 43-file exact public-release controls at `1ce7c359`; the separately gated deployment and read-only audit succeeded.
- **PR #168** — merged append-only deployment receipt history at `5e03e6c9`; the broader platform remains `HOLD`.
- **PR #181** — merged the two guarded VPS repair controls at `40a0463e`; the merge established code and approval boundaries, not execution of either live repair.
- **PR #183** — merged the exact remote repository-security assurance at `6a22b2f7`; the bounded checks passed, while one historical provider-key alert and unenforced `main` protection remain visible `HOLD` gates.
- **PR #184** — merged the newest read-only VPS-runtime receipt into this canonical state at `e4a4aeaa`; the observed runtime verdict remains `ACTION_REQUIRED`, and no VPS mutation was authorized or attempted.
- **PR #64** — superseded by PR #74 and remains conflicted; do not promote it as the current reviewer target.
- **PR #49** — focused external-evaluation protocol candidate.
- **PR #35** — bounded commercial validation-sprint candidate; pricing and traction remain unvalidated.

Use `EVIDENCE_INDEX.md` and `docs/PR_CONSOLIDATION_MAP_2026-07-22.md` for the disposition of the remaining PRs. Preserve superseded branches as lineage unless Robert explicitly authorizes deletion.

## Artifact creation gate

A new artifact is allowed only when all answers are yes:

1. Does it advance one active outcome?
2. Is there no existing canonical artifact that can be updated?
3. Is the audience and decision named?
4. Is the evidence boundary explicit?
5. Will it reduce, rather than expand, the reviewer path?

Otherwise, update the backlog note and stop.

## Clean-checkout protocol gate

The repository-wide test harness distinguishes ordinary clean-checkout checks
from four explicitly named publication or retained-artifact checks. Missing
generated evidence is never treated as a passing validation result: those four
checks are marked artifact-dependent only until their declared files exist.
The authoritative reviewer workflow generates its publications and then runs
the same checks without skips. The frozen CODECHECK source identity remains
byte-identical to its reviewed commit.

## Immediate decision

The next founder-facing actions are to attend the **EPRI / Open Power AI**
Member Representative Committee and selected Work Group meetings, make the
separate founder-controlled EC deposit decision due August 14, and reduce the
active private-review material to one buyer-owned workflow, baseline, metric,
threshold, and go/no-go decision. EPRI / OPAI and EC remain under no-duplicate
holds unless they make a new substantive request.

The named public static release is reconciled at `1ce7c359`, but broader
production promotion remains `HOLD`. The August 12 read-only runtime receipt
against `6a22b2f7`, now recorded on `main` at `e4a4aeaa`, proves only the exact
point-in-time endpoint, identity, source-parity, worker, ledger, and capacity
observations stated above. Do not describe the gateway as down, repaired,
source-complete, or production-authorized. The only prepared live changes are
`REPAIR_PUBLIC_GATEWAY_DEPENDENCY_CLOSURE` and
`REPAIR_PAPER_TICKER_LEDGER_OWNERSHIP`; neither may be dispatched until the
private HumanUnlock secret exists and Robert gives fresh target-specific
authorization at action time.

The next product and revenue gate is one paid or independently executed
Buyer-Owned Baseline Validation Sprint through the existing PR #74 reviewer
surface. Do not create another dashboard, platform, or generic evidence pack.
Agent Arena V5 remains a secondary synthetic fault-injection harness and does
not demonstrate Byzantine tolerance or field performance. PR #67's duplicate
locks and claim boundaries remain intact. The urgent patent action remains
retrieval of the official application record through the USPTO-directed
authenticated or Document Services path. No duplicate or unsolicited outbound
message is authorized. No other outbound message is currently authorized.


## Founder-directed EC cohort contribution - 2026-09-12

Robert's current direction adds a strengths-first cohort contribution: **Our strength is making everyone else stronger.** Energy remains a major research focus. The existing evidence discipline applies to each owner's workflow: understand what already works, identify a testable constraint, agree a baseline and verify the effect. This dated instruction supersedes earlier no-new-EC-outbound statements for the scoped cohort contribution; administrative onboarding and unrelated outreach holds remain.

The [published cohort research](EC_COHORT_STRENGTH_RESEARCH_2026-09-11.md) covers all 69 businesses on the official TakeOff roster, with three hypotheses per company and unknown baselines. Research publication is complete. Owner interviews, participation, measured losses and savings remain unestablished.

On September 12, one resource introduction was sent to both official cohort mailing groups, followed by one direct request to the EC program manager after the AM group returned a delivery failure. Both sends were verified by exact Gmail readback and recorded under `ec-takeoff-strengths-resource`. The AM failure does not distinguish a missing group from posting restrictions. Delivery to individual PM members and any manager redistribution are unconfirmed. Do not retry the group addresses or treat the messages as completed customer conversations. Wait for a substantive response. Exact message content, private identifiers and delivery-failure receipts remain in the existing private review estate.

The 69 public profiles, personalized workspaces and downloadable toolkits were published on the domain at source `5dbdf654caa630923869b3e6d3cf7ace221d5e16`; deployment `34703378307` verified all 189 exact files. The packages include Grant Factory drafts, public-source LumaScout, fictional-funds paper trading, nonclinical LumaCare, measurement tools and optional local AI drafting. Robert delegated the key choice and the existing key was selected; the last inference attempt was blocked by exhausted API credits. No successful AI inference, hosted team deployment, government certification, owner acceptance or savings is established.

At Robert's renewed request, a software-is-live update with a forwardable gift announcement was sent to the same program manager in the existing thread on September 12. Gmail SENT content and Outreach Lock were verified. This makes three scoped outbounds under `ec-takeoff-strengths-resource`; no group retry occurred. Manager forwarding, all-member delivery, six actual customer conversations and owner baselines remain unconfirmed. The earlier in-development text describes the first research note, not the current package availability. The full requested scope remains open.

The member runtime now checks a saved revision before updating its SQLite workspace. Competing browser versions pause backup and offer separate downloads and an owner choice; queued edits wait for the preceding write to finish. Regression checks reproduce the former stale-write overwrite and verify its rejection. This is local data-preservation behavior, not multi-user authorization or external business validation.

The existing Measure & improve view now includes an optional offline energy evidence and constraint review. It preserves the full-batch calculator and records declared service equivalence, source timing, overhead, allowed changes, hard limits, uncertainty and fallback. A candidate can advance only to owner review; every result retains the baseline and disables actuation. Synthetic counterexamples cover net losses, uncertain constraints, missing evidence and binary arithmetic residue. This implements the recommendation-review portion of the research charter without a new dashboard or a performance experiment. Physical metrology, independently accepted results, owner participation, cohort redistribution and successful AI inference remain unestablished. Exact publication and validation receipts stay in the existing private review estate.


## EC portal cohort announcement - 2026-09-12

Robert explicitly provided the signed-in EC portal route and requested delivery of the existing gift announcement. One group-scoped message was posted to TakeOff Fall 2026. The portal confirmed successful sending; the posted title, author, substantive body, public directory link and group recipient list were read back. This is the fourth scoped outbound under `ec-takeoff-strengths-resource`. No email group was retried and no new campaign was created.

The cohort announcement requirement is complete for group posting. Individual notification delivery, reads, owner adoption, six actual customer conversations, baselines and measured results remain unconfirmed. The prior waiting-for-distribution checkpoint is superseded by this verified portal event; other external dependencies remain. Exact portal identifiers, displayed recipients, message text and delivery evidence are retained in the existing private E-drive review estate. Continue substantive replies in that thread or follow new explicit founder direction; do not repost the announcement.


## Frozen breadth review and owner outreach - 2026-09-22

Robert explicitly requested current-work backup, commit, push, merge and publication, together with targeted outreach toward one owner-approved pilot. This dated scope authorizes delivery of this reviewed change; it does not accept commercial terms, authorize spending or establish revenue.

The existing [live breadth proof addendum](LUMENCORE_LIVE_BREADTH_PROOF_ADDENDUM.md) now identifies six retained result cards across five sectors, including two complete public EIA replay windows and all relevant failed gates. Descriptive MAE improvement against the same-feature LightGBM comparator is 10.602% in the original window and 18.509% in the later window. Both remain retrospective, first-party results on potentially revised historical data. They do not establish electricity saved, an operational incumbent win, independent validation or buyer savings. The legacy 921-row infrastructure ledger remains a scenario inventory, with 19 latest source/constraint entries rather than 921 distinct interventions.

The canonical value-panel, multi-asset and truth-chain producers now preserve signed losses, conflicting reports, unknown dollar values and adverse results. Input/intake flags cannot establish accepted economics. The existing buyer-outreach and economic-bridge builders now use source-derived counts, record input identities and staleness, exclude private source detail, and correct a tenfold arithmetic overstatement in illustrative scenarios. Their stale upstream research remains under source-review hold. No new performance experiment or accepted-economic result is claimed by these repairs.

The [proof-to-pilot page](https://lumen-core.ai/proof_to_pilot.html) includes the two-window comparison, evidence limits and a checksum-bound ZIP for external reproduction. The existing signed release lane now names 190 static files, including that exact ZIP; successful deployment must be established by its separate commit-bound receipt. The preceding source 1585909361c0d6e906ab2ad82e4df4c0aae576b9 was reconciled by deployment 35800572553 and a 189-of-189 live check on September 23 UTC. That receipt does not cover this subsequent source change.

Three scoped emails were sent and verified through authoritative SENT readback: two cohort business invitations to choose one measurable workflow, and one ORNL partnership-routing follow-up with the two frozen EIA windows. One requested written tutorial was posted and read back in the existing EC member thread. Dollar examples were explicitly hypothetical staff-capacity arithmetic; no measured client savings were asserted. Exact recipients, messages and receipts remain in the existing private E-drive estate. No reply accepting a pilot, signed contract, license or cleared payment is established by these sends.

The next commercial gate remains an owner, permissioned baseline, metric, prospective observation plan and agreed scope. Continue substantive responses through the existing threads. Maintain the cohort contribution as free, paper-only or nonclinical where applicable. Our strength is making everyone else stronger.

## October 25 dashboard worker liveness correction (local review)

Outcome 2: reliable reviewer evidence generation. The local dashboard worker
now uses the gateway's query-only Windows process-check pattern instead of
`os.kill(pid, 0)`. Access failures and malformed owner records preserve the
existing lock; only a confirmed absent owner permits reclamation. Native
Windows and portable API-error regressions cover the correction, with a
Windows job added to the existing snapshot gate. This is local software
validation, not independent evaluation or runtime deployment. The separately
prepared Mission Control PR #261 release remains unchanged.
