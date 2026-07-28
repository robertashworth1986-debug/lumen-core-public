# Outreach Response Template Registry - 2026-07-18

- Templates: `17`
- Private-render templates: `12`
- Builder can send email: `false`
- Duplicate-send gate: `FAIL_CLOSED`
- Missing-fact gate: `FAIL_CLOSED`
- Past-deadline gate: `FAIL_CLOSED`
- Inserted-fact claim gate: `FAIL_CLOSED`
- High-risk claim evidence: `EXACT_VALUE_AND_SOURCE_HASH_BOUND`
- Ready-render dispatch scope: `RECIPIENT_THREAD_BODY_DEADLINE_EVIDENCE_HASH_BOUND`
- Attachment content required for exact approval: `true`
- Draft binding is send authorization: `false`
- Action-time mailbox receipt: `REQUIRED`
- Action-time mailbox freshness: `15_MINUTES_MAX`
- Exact approval phrase: `BINDING_SCOPED_SINGLE_USE`
- Exact approval window: `5_MINUTES_MAX`
- Private HumanUnlock: `REQUIRED_AT_RUNTIME`
- Dispatch handoff can send email: `false`
- Static quality gate: `PASS`
- Static quality checks: `204`
- Unchanged rebuilds byte-stable: `true`

## Claim Boundary

This response is a communication or routing artifact. It does not establish selection, endorsement, independent validation, funding, an award, a contract, deployment, realized savings, or technical performance.

## Global Rules

- Ground every reply in the latest inbound message and preserve its thread identifier.
- Answer only the question asked; do not append an unrelated pitch or attachment.
- Do not send a duplicate when the requested information or packet is already in the thread.
- Never imply independent validation, field performance, selection, funding, or savings without direct evidence.
- Keep legal, signatory, address, account, and portal identifiers in private renderings only.
- Attach files only when the recipient or governing instructions explicitly require them.
- Escalate deadlines with the exact date, time, timezone, portal, and observed blocker.
- Render the same canonical timezone-aware deadline_iso value that the urgency gate evaluates for every template that states a known deadline.
- Use HTTPS-only public links without embedded credentials.
- Reject rendered subject lines containing line breaks or other mail-header injection characters.
- Require action-time human review for every outbound response.

## Quality Gate

- All templates pass: `true`
- Deadline-control templates: `COMPONENT_INSTRUCTION_ESCALATION, INITIAL_PARTNER_TEAMING_INQUIRY, PORTAL_SUPPORT_DEADLINE_RESCUE`
- HTTPS public URL fields: `6`

## Decision Matrix

| Template | Send policy | Attachment policy | Private render |
|---|---|---|---:|
| `NO_DUPLICATE_MONITOR` | `MONITOR_NO_SEND` | `NONE` | `false` |
| `NO_DUPLICATE_MEETING_PREP` | `MONITOR_NO_SEND` | `NONE` | `false` |
| `DEADLINE_CLARIFICATION` | `HUMAN_ACTION_DUE` | `NONE` | `false` |
| `PORTAL_SUPPORT_DEADLINE_RESCUE` | `HUMAN_ACTION_DUE` | `EXPLICIT_REQUEST_ONLY` | `true` |
| `REQUESTED_INFORMATION_REPLY` | `REPLY_AFTER_FACT_REVIEW` | `EXPLICIT_REQUEST_ONLY` | `true` |
| `REQUESTED_ASSET_DELIVERY_REPLY` | `REPLY_AFTER_FACT_REVIEW` | `EXPLICIT_REQUEST_ONLY` | `true` |
| `SUBMISSION_RECEIPT_FOLLOWUP` | `REPLY_AFTER_FACT_REVIEW` | `NONE` | `true` |
| `COMPONENT_INSTRUCTION_ESCALATION` | `HUMAN_ACTION_DUE` | `NONE` | `true` |
| `BOUNDED_REVIEW_FOLLOWUP` | `HUMAN_ACTION_DUE` | `NONE` | `true` |
| `WARM_INVESTOR_INTRO_REQUEST` | `HUMAN_ACTION_DUE` | `NONE` | `true` |
| `FUNDING_REVIEW_STATUS_CHECK` | `HUMAN_ACTION_DUE` | `NONE` | `true` |
| `DIRECT_INVESTOR_REVIEW_REQUEST` | `HUMAN_ACTION_DUE` | `NONE` | `true` |
| `INITIAL_PARTNER_TEAMING_INQUIRY` | `HUMAN_ACTION_DUE` | `NONE` | `true` |
| `VALIDATION_PILOT_REQUEST` | `REPLY_AFTER_FACT_REVIEW` | `EXPLICIT_REQUEST_ONLY` | `false` |
| `DECLINE_CLOSEOUT` | `REPLY_AFTER_FACT_REVIEW` | `NONE` | `false` |
| `MOU_ONBOARDING_REPLY` | `REPLY_AFTER_FACT_REVIEW` | `NONE` | `true` |
| `MEETING_REBOOK_REQUEST` | `HUMAN_ACTION_DUE` | `NONE` | `true` |

## NO_DUPLICATE_MONITOR

Use after a receipt, out-of-office notice, completed answer, or final decline when no new question requires a reply.

- Inbound states: `RECEIPT_CONFIRMED, OUT_OF_OFFICE, ALREADY_ANSWERED, DECLINE_FINAL`
- Reply triggers: `NEW_FACT_REQUEST, CORRECTION_REQUEST, MOU_RECEIVED, PORTAL_INSTRUCTION`
- Required fields: `none`

No message is rendered. Monitor the thread and do not duplicate-send.

## NO_DUPLICATE_MEETING_PREP

Use when one calendar invitation already exists and the meeting is confirmed or accepted; prepare evidence and monitor the existing event without sending another reply or invitation.

- Inbound states: `MEETING_CONFIRMED, CALENDAR_INVITE_ACCEPTED, MEETING_PREP_DUE`
- Reply triggers: `SCHEDULE_CHANGE, NEW_MEETING_QUESTION, ATTENDANCE_PROBLEM`
- Required fields: `none`

No message is rendered. Monitor the thread and do not duplicate-send.

## DEADLINE_CLARIFICATION

Ask an authoritative contact to confirm the exact deadline or eligibility rule before a package is finalized.

- Inbound states: `DEADLINE_AMBIGUOUS, ELIGIBILITY_AMBIGUOUS`
- Reply triggers: `AUTHORITATIVE_CLARIFICATION_NEEDED`
- Required fields: `recipient_name, source_subject, opportunity_name, eligibility_question, sender_name, sender_title, organization_name, recipient_email, source_message_id`

```text
Subject: Re: {source_subject}

Hello {recipient_name},

I am finalizing {opportunity_name}. Please confirm the official submission deadline, including timezone, and whether {eligibility_question}.

If a portal-specific instruction controls, please send the authoritative link or section.

Thank you,
{sender_name}
{sender_title}
{organization_name}
```

## PORTAL_SUPPORT_DEADLINE_RESCUE

Request official support instructions for a concrete portal blocker before a known close time.

- Inbound states: `PORTAL_BLOCKER, SUBMISSION_AT_RISK`
- Reply triggers: `SUPPORT_ACTION_REQUIRED`
- Required fields: `recipient_name, submission_name, portal_name, deadline_iso, portal_blocker, steps_already_tried, sender_name, sender_title, organization_name, recipient_email, source_message_id`

```text
Subject: Time-sensitive portal support: {submission_name}

Hello {recipient_name},

I am attempting to complete {submission_name} in {portal_name} before {deadline_iso}. The current blocker is: {portal_blocker}

Steps already tried: {steps_already_tried}

Please confirm the safest supported path to preserve a timely submission. I am not asking for requirements to be waived; I need the official instructions for resolving this blocker before close.

Thank you,
{sender_name}
{sender_title}
{organization_name}
```

## REQUESTED_INFORMATION_REPLY

Answer a specific inbound fact request without adding unrelated claims or attachments.

- Inbound states: `INFORMATION_REQUESTED, CORRECTION_REQUESTED`
- Reply triggers: `FACTUAL_RESPONSE_REQUIRED`
- Required fields: `recipient_name, source_subject, requested_information, sender_name, sender_title, organization_name, recipient_email, source_message_id`

```text
Subject: Re: {source_subject}

Hello {recipient_name},

Thank you. Below is the requested information, limited to your question:

{requested_information}

Please let me know if any item needs correction before it is placed into an agreement, portal record, or formal submission.

Best regards,
{sender_name}
{sender_title}
{organization_name}
```

## REQUESTED_ASSET_DELIVERY_REPLY

Deliver only files explicitly requested in an inbound message, with a bounded inventory and permitted-use statement.

- Inbound states: `ASSETS_EXPLICITLY_REQUESTED, REQUESTED_ASSETS_READY_FOR_REVIEW`
- Reply triggers: `EXPLICIT_ASSET_DELIVERY_REQUEST`
- Required fields: `recipient_name, source_subject, requested_asset_summary, attachment_inventory, permitted_use_boundary, sender_name, sender_title, organization_name, recipient_email, source_message_id`

```text
Subject: Re: {source_subject}

Hello {recipient_name},

Attached are only the materials explicitly requested in your message: {requested_asset_summary}

Attachment inventory: {attachment_inventory}

Permitted use: {permitted_use_boundary}

These materials do not imply endorsement, independent validation, licensing beyond the stated use, an award, or a performance claim. Please let me know if you need a different file format or dimensions.

Best regards,
{sender_name}
{sender_title}
{organization_name}
```

## SUBMISSION_RECEIPT_FOLLOWUP

Confirm delivery and readability after a required package was sent; this is not a duplicate submission.

- Inbound states: `SUBMISSION_SENT_NO_RECEIPT, RECEIPT_UNCERTAIN`
- Reply triggers: `RECEIPT_CONFIRMATION_REQUIRED`
- Required fields: `recipient_name, source_subject, submitted_at_local, submission_name, notice_or_topic, artifact_names, sender_name, sender_title, organization_name, recipient_email, source_message_id`

```text
Subject: Re: {source_subject}

Hello {recipient_name},

On {submitted_at_local}, I sent {submission_name} under {notice_or_topic}. The transmitted files were: {artifact_names}.

Could you confirm receipt and whether anything is missing or unreadable? This is a receipt check only, not a duplicate submission.

Thank you,
{sender_name}
{sender_title}
{organization_name}
```

## COMPONENT_INSTRUCTION_ESCALATION

Follow up once with the authoritative component POC after portal support redirects a deadline-critical instruction question and the original component message remains unanswered.

- Inbound states: `SUPPORT_REDIRECTED_TO_COMPONENT, DEADLINE_BLOCKER_UNANSWERED`
- Reply triggers: `COMPONENT_POC_FOLLOWUP_AFTER_NO_REPLY`
- Required fields: `recipient_name, source_subject, topic_or_notice, deadline_iso, original_sent_local, support_redirect_summary, exact_instruction_question, requested_reply_by_local, sender_name, sender_title, organization_name, recipient_email, source_message_id`

```text
Subject: Re: {source_subject}

Hello {recipient_name},

I am following up once on the instruction question below for {topic_or_notice}, which closes {deadline_iso}. The original component message was sent {original_sent_local}. {support_redirect_summary}

Question requiring component guidance: {exact_instruction_question}

I will not treat prerequisites-in-progress as completed evidence or represent an uncompleted certification. A response by {requested_reply_by_local} would leave time to follow the official instruction before close. No attachment is included, and I will not duplicate the proposal package by email.

Thank you,
{sender_name}
{sender_title}
{organization_name}
```

## BOUNDED_REVIEW_FOLLOWUP

Send one claim-bounded follow-up after a reviewed package and a defined hold, asking whether a short diligence or evaluation-fit discussion is useful.

- Inbound states: `PACKAGE_SENT_RESPONSE_PENDING`
- Reply triggers: `HOLD_EXPIRED_NO_REPLY_AFTER_RECHECK`
- Required fields: `recipient_name, source_subject, sent_date_local, package_name, review_scope, requested_next_step, sender_name, sender_title, organization_name, recipient_email, source_message_id`

```text
Subject: Re: {source_subject}

Hello {recipient_name},

I am following up once on {package_name}, sent {sent_date_local}. Would {requested_next_step} be useful to decide whether a bounded review is warranted?

Proposed scope: {review_scope}

This note does not assert receipt, endorsement, independent validation, licensing, funding, deployment, or production readiness. No additional attachment is included. If this is not a fit, no response is required and I will not send another follow-up.

Best regards,
{sender_name}
{sender_title}
{organization_name}
```

## WARM_INVESTOR_INTRO_REQUEST

Follow up once after a funding contact explicitly offered introductions, narrowing the request to one primary and one secondary fit without attaching another deck.

- Inbound states: `WARM_INTRO_OFFER_NO_REPLY`
- Reply triggers: `ONE_FOCUSED_INTRO_FOLLOWUP_AFTER_HOLD`
- Required fields: `recipient_name, source_subject, current_raise_amount, current_raise_purpose, primary_fund_name, primary_fit_reason, secondary_fund_name, public_proof_url, current_stage_disclosure, sender_name, sender_title, organization_name, recipient_email, source_message_id`

```text
Subject: Re: {source_subject}

Hello {recipient_name},

I am following up once on your offer to make a targeted introduction. {organization_name}'s current ask is {current_raise_amount} for {current_raise_purpose}.

If you still see a fit, would you please introduce me to {primary_fund_name} first? {primary_fit_reason} {secondary_fund_name} would be my second choice.

Current public proof: {public_proof_url}

Current stage and claim boundary: {current_stage_disclosure}

No attachment is included. If this is no longer a fit, no response is required and I will not send another introduction follow-up.

Thank you,
{sender_name}
{sender_title}
{organization_name}
```

## FUNDING_REVIEW_STATUS_CHECK

Ask once whether a funding application remains active and complete after the review window stated by the recipient has passed.

- Inbound states: `FUNDING_REVIEW_WINDOW_PASSED`
- Reply triggers: `ONE_STATUS_CHECK_AFTER_STATED_WINDOW`
- Required fields: `recipient_name, source_subject, application_name, application_date_local, stated_review_window, duplicate_review_disclosure, sender_name, sender_title, organization_name, recipient_email, source_message_id`

```text
Subject: Re: {source_subject}

Hello {recipient_name},

I am following up once on {application_name}, submitted {application_date_local}. Your note stated a review window of {stated_review_window}. Could you confirm whether the application is still active and complete for review?

Duplicate-send check: {duplicate_review_disclosure}

This is a status check only, not a duplicate application. No new attachment is included unless your team requests one.

Thank you,
{sender_name}
{sender_title}
{organization_name}
```

## DIRECT_INVESTOR_REVIEW_REQUEST

Send one public-safe request to a verified investor or program route when no prior outreach exists, with no attachment and an explicit stage boundary.

- Inbound states: `VERIFIED_DIRECT_INVESTOR_ROUTE_NO_PRIOR_THREAD`
- Reply triggers: `ONE_INITIAL_DIRECT_INVESTOR_REVIEW_REQUEST`
- Required fields: `recipient_name, investor_program_name, company_one_line, current_raise_amount, current_raise_purpose, six_month_milestone, climate_component, current_stage_disclosure, public_company_url, public_proof_url, sender_name, sender_title, organization_name, recipient_email`

```text
Subject: {organization_name} - {current_raise_amount} validation bridge for {investor_program_name}

Hello {recipient_name},

I am {sender_name}, {sender_title} of {organization_name}. {company_one_line}

I am requesting a review for {investor_program_name}. Our current ask is {current_raise_amount} for {current_raise_purpose}. The six-month milestone is {six_month_milestone}

Climate-positive component: {climate_component}

Current stage and claim boundary: {current_stage_disclosure}

Company: {public_company_url}
Public proof: {public_proof_url}

No attachment is included. If this is not the correct route, would you please direct me to the official application channel? I will not send a duplicate initial request.

Thank you,
{sender_name}
{sender_title}
{organization_name}
```

## INITIAL_PARTNER_TEAMING_INQUIRY

Send one no-attachment fit-check to a verified public corporate route for an active opportunity that permits teaming, while preserving qualification and partner-authority boundaries.

- Inbound states: `VERIFIED_PUBLIC_PARTNER_ROUTE_NO_PRIOR_THREAD`
- Reply triggers: `ONE_INITIAL_BOUNDED_TEAMING_INQUIRY`
- Required fields: `recipient_name, agency_name, opportunity_name, notice_type, opportunity_summary, deadline_iso, teaming_basis, bounded_contribution, qualification_boundary, partner_fit_basis, requested_partner_role, authorization_request, duplicate_review_disclosure, source_opportunity_url, public_company_url, public_proof_url, sender_name, sender_title, organization_name, recipient_email`

```text
Subject: Time-sensitive teaming inquiry - {opportunity_name}

Hello {recipient_name},

I am {sender_name}, {sender_title} of {organization_name}. {agency_name} posted {opportunity_name}, a {notice_type}: {opportunity_summary}

The official response deadline is {deadline_iso}. {teaming_basis}

Our bounded contribution is {bounded_contribution}

Qualification boundary: {qualification_boundary}

Partner fit basis: {partner_fit_basis}

Would your organization be open to a rapid fit check for the following role: {requested_partner_role}

Before either organization is named or any credential is used, we need written confirmation of: {authorization_request}

Duplicate-send check: {duplicate_review_disclosure}

This inquiry requests a nonbinding fit check only. It does not request pricing, a commitment, or permission to represent an unverified qualification. No attachment is included. A prompt reply would preserve time for both parties to reconcile an accurate response before the official deadline.

Official notice: {source_opportunity_url}
Company: {public_company_url}
Public proof: {public_proof_url}

Respectfully,
{sender_name}
{sender_title}
{organization_name}
```

## VALIDATION_PILOT_REQUEST

Invite a qualified reviewer to define a bounded, independently reproducible evaluation rather than endorse a broad platform claim.

- Inbound states: `VALIDATION_ROUTE_OPEN, PILOT_SCOPE_REQUESTED`
- Reply triggers: `BOUNDED_REVIEW_PROPOSAL`
- Required fields: `recipient_name, source_subject, problem_lane, validation_scope, protocol_summary, requested_next_step, sender_name, sender_title, organization_name, recipient_email, source_message_id`

```text
Subject: Re: {source_subject} - bounded validation scope

Hello {recipient_name},

Thank you for considering {problem_lane}. We are requesting a bounded review, not an endorsement. The current evidence is internal and has not been independently reproduced.

Proposed evaluation scope: {validation_scope}
Protocol: {protocol_summary}

The evaluation should lock the incumbent baseline and acceptance metrics before scoring, use reviewer-controlled or authorized data, retain negative results, and separate receipt integrity from substantive performance.

Requested next step: {requested_next_step}

Best regards,
{sender_name}
{sender_title}
{organization_name}
```

## DECLINE_CLOSEOUT

Acknowledge a final decline professionally and stop the current outreach lane without repitching.

- Inbound states: `DECLINE_FINAL, TEAM_ALREADY_SET, SERVICE_NOT_OFFERED`
- Reply triggers: `COURTESY_CLOSEOUT_DUE`
- Required fields: `recipient_name, source_subject, future_fit, sender_name, sender_title, organization_name, recipient_email, source_message_id`

```text
Subject: Re: {source_subject}

Hello {recipient_name},

Thank you for the clear answer. I appreciate your time and will not send a duplicate packet on this lane.

If a future opportunity specifically matches {future_fit}, I would welcome a fresh invitation.

Best regards,
{sender_name}
{sender_title}
{organization_name}
```

## MOU_ONBOARDING_REPLY

Provide exactly the legal-party and signatory facts requested for an MOU while requiring private handling and pre-issuance confirmation.

- Inbound states: `MOU_INFORMATION_REQUESTED`
- Reply triggers: `LEGAL_PARTY_FACTS_REQUIRED`
- Required fields: `recipient_name, source_subject, legal_party_name, organization_name, business_address, signatory_name, signatory_email, signatory_title, sender_name, sender_title, recipient_email, source_message_id`

```text
Subject: Re: {source_subject}

Hello {recipient_name},

Thank you. Please use the following information for the MOU:

Full legal party name: {legal_party_name}
Organization or project name: {organization_name}
Business address: {business_address}

Signatory name: {signatory_name}
Signatory email: {signatory_email}
Signatory title: {signatory_title}

Please confirm the exact entity format before issuing the agreement or DocuSign envelope if your records require a different legal-party convention.

Best regards,
{sender_name}
{sender_title}
{organization_name}
```

## MEETING_REBOOK_REQUEST

Correct a scheduling mistake, confirm continued interest, and request a specific rebooking path without oversharing.

- Inbound states: `MEETING_MISSED, TIMEZONE_ERROR, REBOOK_REQUIRED`
- Reply triggers: `SCHEDULING_RESPONSE_REQUIRED`
- Required fields: `recipient_name, source_subject, meeting_context, scheduling_correction, availability_windows, sender_name, sender_title, organization_name, recipient_email, source_message_id`

```text
Subject: Re: {source_subject}

Hello {recipient_name},

I apologize for the scheduling mistake regarding {meeting_context}. {scheduling_correction}

I remain interested and can meet during: {availability_windows}. Please use whichever available slot is easiest, or send the correct rebooking link.

Thank you,
{sender_name}
{sender_title}
{organization_name}
```

## Operating Boundary

This registry renders drafts, immutable dispatch bindings, action-time authorization records, and routing decisions only. It does not access Gmail, transmit a message, certify facts, authorize an attachment, or replace action-time human review. A ready render receives a binding over the recipient route, source thread, exact subject and body, deadline, evidence receipts, and attachment set, but that draft binding is not send authorization. An exact approval phrase is withheld until every attachment content hash is bound and a fresh full-mailbox search plus exact draft readback confirm one current unsent draft, no matching sent copy, no later inbound response, and no CC or BCC. The resulting exact phrase is hash-bound, single-use, and valid for no more than five minutes or until the deadline, whichever comes first. Dispatch authorization additionally requires a private HumanUnlock checked only at runtime; the token and expected hash are omitted from receipts, and the evaluator cannot send. A binding scopes approval; it is not proof of transmission, receipt, content truth, independent validation, agency acceptance, field performance, savings, an award, or any other real-world outcome.
