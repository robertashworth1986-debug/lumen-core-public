# Current Federal Opportunity Gate Map

Snapshot: 2026-08-05
Mode: official-source triage; no portal submission authorized

Monday reconciliation: 2026-07-27T20:12:08Z. The July 27 CSDR and NSF lanes
were rechecked against the mailbox and official-source gates. Neither lane
authorizes a new external action.

## Control Rules

- Official solicitation pages, attachments, amendments, and portal state are
  the action-time source of truth.
- Drafted, sent, and submitted are separate states.
- Login.gov and connected portals remain human-operated. No automated sign-in,
  certification, representation, signature, upload, or submission is authorized.
- A short deadline does not justify a knowingly false capability statement.
- Every send requires a fresh duplicate check and exact action-time approval of
  recipient, subject, body, and attachments.
- The machine-checkable [Deadline Action Sentinel](DEADLINE_ACTION_SENTINEL.md)
  preserves exact deadlines where the source supports them and fails closed on
  date-only milestones, unknown timezones, and every external action.

## Deadline Map

| Priority | Lane | Exact deadline | Current fit and gate | Position | Current state | Safest next action |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | [DAF CSDR Support and Curation CSO, FA701426SCS01](https://sam.gov/opp/a7d2947ffb4e43e28cf136925e59e580/view) | July 27, 2026, 1:00 PM EDT | Total small-business CSO, but the notice requires direct CSDR/FlexFile experience, qualified cost-data leadership, key personnel, and security qualifications that the public evidence does not establish. | `TEAM_OR_PASS` | One bounded no-attachment capability email was sent July 24. No inbound reply or formal Step 1 white-paper receipt was found. The deadline has passed; no late or duplicate response is authorized. | Monitor only for an inbound Government or qualified-prime request. |
| 2 | [NSF SBIR/STTR 26-510](https://www.nsf.gov/funding/opportunities/small-business-innovation-research-small-business-technology/nsf26-510/solicitation) | July 27, 2026, 5:00 PM submitting organization's local time; next deadline November 4, 2026 | A Phase I or Fast-Track Project Pitch invitation is mandatory. No official invitation was found in the full-mailbox audit. | `TARGET_NEXT_CYCLE` | July 27 route is closed by the invitation gate, not by document quality. No portal action is authorized. | Build one bounded Project Pitch for the November cycle after selecting the prospective research lane and resolving eligibility facts. |
| 3 | [HHS Project Argos Sources Sought, ONC-ARGOS-SSN-2026-OS351107](https://sam.gov/opp/062cef11f5384443bfd84bf123404026/view) | July 30, 2026, 5:00 PM EDT | Strong fit for evidence custody, deterministic validation, traceability, human gates, and reviewer packages. FHIR R4/CHPL/ONC and HHS ATO/3PAO qualifications remain gaps. This is market research, not an award. | `SENT_ONCE_WAITING` | Exactly one bounded response was transmitted July 28 CT. An automatic out-of-office reply establishes mailbox-system reach only; formal receipt, review, acceptance, selection, award, funding, and validation are not confirmed. | Do not resend. Wait for a substantive HHS request and reply only in the existing thread after a fresh duplicate check and exact approval. |
| 4 | [DoDEA Data and AI Modernization Support, DoWEA-PSN-26-002](https://sam.gov/opp/dc22bd38118e4d739579e8e5f6fcf0bb/view) | July 29, 2026, 4:00 PM EDT is the posted presolicitation date; no final offer deadline is issued | Data architecture, governance, analytics, AI integration, literacy, program management, and student-information-system modernization are relevant, but enterprise modernization and education/SIS delivery depth are not established. | `MONITOR_AND_TEAM` | Presolicitation only. It does not authorize or require a final proposal by July 29. | Watch for the formal RFP and seek a qualified enterprise/education prime before deciding whether to build a response. |
| 5 | [FHWA TSMO Data Initiative, 693JJ326R000012](https://sam.gov/workspace/contract/opp/82cfdcdb95ae40a7b70dba615c31f89b/view) | August 3, 2026, 9:00 AM EDT | The full-and-open solicitation sought AI prototypes for transportation-system data challenges. LumenCore's evidence controls were relevant, but transportation/TSMO delivery experience, a complete proposal team, and attachment-level compliance were not established. | `CLOSED_NO_LATE_RESPONSE` | The posted deadline has passed. No compliant solo proposal or qualified teaming route was established before the cutoff. | Preserve the research notes. Do not submit late or create post-deadline outreach unless the contracting office issues a new official route. |
| 6 | [NSF Energy-Water Security Consortium BAA, 49100426R0009](https://sam.gov/opp/643cf86fd0cd439590f6f6dce2aaaa36/view) | August 6, 2026, 5:00 PM EDT | Coupled energy-water modeling, reproducible measurement, and evidence-controlled evaluation may fit. The BAA seeks a real consortium and deployment pathway; LumenCore alone is not established as the consortium lead. | `CONSORTIUM_TEAM` | Potential real-award lane; full BAA attachment, consortium identity, roles, regional/domain partners, budget, and submission channel remain open gates. | Confirm the signed consortium's actual identity and scope, then build a requirement matrix before authorizing any proposal effort. |
| 7 | [DLA Emergent IV R&D BAA, BAA0001-22](https://sam.gov/opp/fa3397955dc6425ea99b7f3416b4a3b7/view) | June 12, 2027, 5:00 PM EDT; latest Area-of-Interest instructions control | Potential fit exists in logistics-data interoperability, digital modernization, AI/ML, and inspectable evidence workflows. The BAA accepts an initial white paper and may invite a technical and cost proposal. It is not near-term cash and does not establish that any current Area of Interest accepts LumenCore's exact scope. | `VERIFY_AOI_THEN_WHITE_PAPER` | Active through Amendment 37. Latest attachment, Area of Interest, white-paper template, rights, security, cost, and transition requirements have not yet been reconciled. | Build an amendment-to-requirement matrix for one exact Area of Interest before drafting or contacting DLA. |
| 8 | [DLA / DoD SBIR-STTR Release 4](https://www.dla.mil/Small-Business/Vendor-Opportunities/Small-Business-Innovation-Programs/source/GovDelivery/) | August 19, 2026; exact DSIP deadline and topic instructions must be rechecked | The public DLA schedule shows Release 4 open July 22 through August 19. DLA identifies CMMC training, FOCI training, and EJCP access controls; topic-specific eligibility and technical-data gates still control. | `TOPIC_MATCH_REQUIRED` | The prior `DLA26BZ03-NV011` lane is closed: DLA confirmed its DSIP state remained `In Progress` and it was not formally submitted. No current Release 4 topic has yet been proven to match the repository evidence. | Read the current public DSIP topic package, rank only exact matches, and preserve JCP/EJCP, CMMC, FOCI, SAM, and submission gates. |
| 9 | [DARPA FALCON, DPA26BZ04-DV016](https://www.darpa.mil/work-with-us/opportunities/dpa26bz04-dv016) | August 19, 2026, 12:00 PM ET | Structured-data analysis is relevant, but the topic requires a credible Phase II-scale technical and transition case. The current public evidence supports reproducibility methods, not broad SOTA or field claims. | `TEAM_OR_HIGH_GATE_PRIME` | Research fit exists; prior-performance, transition, rights, budget, and team gates remain open. | Obtain the full topic package, build a requirement matrix, and seek a qualified transition/mission partner before deciding to prime. |
| 10 | [NIST AI Consortium letter of interest](https://www.nist.gov/artificial-intelligence/nist-ai-consortium/submit-letter-interest-join-nist-ai-consortium) | Ongoing; NIST says reviews are likely biannual | The consortium can support standards and measurement engagement, but membership would require a later CRADA and does not establish endorsement, validation, funding, or compliance. | `FOUNDER_CONTROLLED_LOI_OPTION` | The NIST page was rechecked August 5, 2026. It now displays OMB expiration August 31, 2026 and says LOIs are accepted on an ongoing basis with regular review periods likely occurring biannually. | Treat the LOI as optional standards engagement, not a deadline rescue. Any webform, email, hardcopy LOI, or later CRADA remains founder-controlled and requires action-time legal review; do not submit automatically. |
| 11 | [MARAD FY26 U.S. Marine Highway Program](https://simpler.grants.gov/opportunity/e9fcef79-7815-4c75-b588-869d82196405) | August 31, 2026, 11:59:59 PM EDT | A private applicant must be a U.S. operator of a Marine Highway Project or owner of an eligible facility and must have a current Route Sponsor endorsement; match and project authority also control. | `NO_GO_SOLO_PARTNER_GATED` | The current Grants record is Version 6, updated July 29, and explicitly open. LumenCore has not established the required maritime operator/facility role, route-sponsor endorsement, project authority, or matching funds. | Do not build or submit a solo application. Reconsider only if a qualified operator/facility owner and Route Sponsor establish a real bounded role and the founder approves the financial structure. |
| 12 | [NSF AI Datasets, NSF 26-512](https://www.nsf.gov/funding/opportunities/ai-datasets-unlocking-dataset-value-ai-enabled-scientific-discovery/nsf26-512/solicitation) | November 4, 2026, 5:00 PM submitting organization's local time | The program funds work that enhances existing scientific datasets and their community value; de novo dataset collection is out of scope. | `PLANNING_GRANT_DATASET_GATE` | A planning proposal may fit only after a real scientific dataset, committed research community, governance, security/integrity, availability, adoption, and sustainment path are established. A generic platform proposal is not enough. | Identify one existing scientific dataset and committed community owner before investing in a planning proposal. Do not imply dataset rights, adoption, or community support without evidence. |
| 13 | [ALCF Director's Discretionary Allocation](https://www.alcf.anl.gov/science/directors-discretionary-allocation-program) | Rolling, year-round | Noncash compute supports prospective, topology, or thermal experiments if leadership-class need and scale readiness are demonstrated. | `DIRECT_RESEARCH_RESOURCE` | Eligible in principle; no allocation or storage award is claimed. | Select one preregistered experiment, estimate scaling need, and prepare a truthful compute-readiness request. |
| 14 | [NSF PESOSE 26-506](https://www.nsf.gov/funding/opportunities/pesose-pathways-enable-secure-open-source-ecosystems/nsf26-506/solicitation) | September 1, 2026, 5:00 PM submitting organization's local time | Requires an existing public open-source product plus three to five letters from unrelated current users or contributors. Organization and PI eligibility also apply. | `CONDITIONAL_PARTNER_OR_FUTURE` | Public code exists; qualifying third-party ecosystem evidence is not yet established. | Do not manufacture letters. Verify lead eligibility and obtain genuine user/contributor evidence before investing in a proposal. |
| 15 | [DOE FY26 Phase I Genesis Mission](https://sbir-sttr.connectwerx.org/) | September 10, 2026, 2:00 PM, portal source should be rechecked for timezone | Potential fit only for a concrete autonomous-laboratory or Genesis topic workflow with a falsifiable technical objective and credible research/transition team. | `RESEARCH_PARTNER_FIRST` | Application hub is active; account/AMP and topic-specific gates require action-time review. | Download the official topic package, choose one exact subtopic, and build a no-claims-gap matrix before portal work. |

## Explicit Pass Lanes

- [USMC AI-Enabled Manpower Modeling, M6786126IMKMAI](https://sam.gov/workspace/contract/opp/d8b87f71b9af4563804e6addf0cce898/view):
  pass as a solo response. The July 30 market-research request requires
  personnel/readiness domain depth, secure DoD deployment, PII/CUI controls,
  RMF/ATO, and cybersecurity evidence that is not currently established.
- [FMCSA Advanced Transportation Analytics Platform, 693JJ4-26-RFI-0003](https://sam.gov/opp/09417109523d4f10ad7a98b1c26befd0/view):
  pass unless an established platform provider requests a bounded evidence
  role. The August 5 RFI asks for an operational platform, real-time APIs,
  transportation/fraud expertise, relevant past projects, and documented data
  rights.
- [HUD Independent Model Validation, FY26IMV](https://sam.gov/opp/137d018082b247b2867052f83cae9683/view):
  pass unless a mortgage/actuarial prime requests LumenCore's reproducibility
  workstream. The July 31 sources-sought route requires FHA mortgage-finance,
  actuarial, investment-risk, and independent-validation experience that the
  public evidence does not establish.

## Portal Readiness

Open these official routes directly when the user is ready to act:

- SAM.gov Workspace for contract responses;
- DSIP for DoD SBIR/STTR topics;
- Research.gov or Grants.gov for NSF opportunities, as allowed by the notice;
- DOE/ConnectWerx Acquisition Management Portal for Genesis Mission;
- ALCF allocation request system for noncash compute.

### Discovery, rules, and award-intelligence services

These services support research but are not interchangeable with submission
portals:

- [SAM.gov Data Services](https://sam.gov/data-services/Documentation?privacy=Public)
  provides documented public APIs and bulk extracts. Use only sanctioned public
  interfaces under their current terms; never scrape a signed-in workspace.
- [Acquisition.gov](https://www.acquisition.gov/browse/index/far?frame=0) is the
  official FAR and agency-acquisition-regulation library. It is used to
  interpret solicitation clauses, certifications, evaluation rules, and
  contract obligations; it is not where LumenCore submits a bid.
- [USAspending.gov](https://www.usaspending.gov/data/data-sources-download.pdf)
  publishes federal award-history data. Use it to identify actual buying
  offices, incumbents, award size, NAICS/PSC patterns, and follow-on timing; it
  is not an opportunity or application portal.
- [USA.gov](https://www.usa.gov/benefits) routes individuals to official
  benefits and financial-assistance information. It is not a company
  contracting portal.

Being signed in does not resolve entity registration, UEI, representations and
certifications, AOR, PI, teaming, security, cost-share, invitation, or
opportunity-specific eligibility gates. Those facts must be verified for each
lane before upload or submission.

## Current Decision

There is no verified, action-safe solo-prime submission inside the next
72 hours. The FHWA deadline has passed, Argos is locked after one transmission,
and the August 6 Energy-Water lane remains consortium-gated. No late, duplicate,
or unsupported response is authorized.

The strongest near-term federal work is decision gating rather than another
submission package: verify whether FALCON's Direct-to-Phase-II evidence threshold
can be met with a qualified team; keep MARAD a no-go unless a real eligible
operator/facility owner and Route Sponsor establish the required role; and treat
the NIST LOI as optional standards engagement that still requires founder
approval and legal review before any webform, email, hardcopy submission, or
CRADA path. Longer-horizon research effort should move to an
existing-dataset/community gate for NSF 26-512, a verified DLA Emergent IV Area
of Interest, DLA Release 4 topic matching, DOE Genesis topic selection, and a
rolling ALCF compute request tied to a preregistered experiment.
