# MissionWeave JCP Support Escalation

**State:** `HOLD_MISSING_READINESS_CONTROLS_AND_HUMAN_UNLOCK`

**Deadline:** 2026-07-22 12:00 PM Eastern / 11:00 AM Central

**Route:** `missionweave_jcp_portal_support`

**Send performed:** `false`

## Decision Controls

- [x] `component_route_duplicate_block_preserved`
- [x] `draft_contains_no_attachment`
- [x] `fresh_duplicate_check_confirmed`
- [ ] `founder_review_confirmed`
- [x] `gmail_draft_created`
- [x] `portal_receipt_reconciled_privately`

The existing DSIP/component follow-up lane remains exhausted and must not be
reused. This is a separate JCP portal-support route. Even when every readiness
check is true, this builder never sends email and never sets `send_authorized`
to true. The action-time phrase is:

`SEND ONE JCP URGENT SUPPORT REQUEST`

## Draft

**To:** jcp-admin@dla.mil

**Subject:** Urgent JCP portal status sync before DLA SBIR deadline - DLA26BZ03-NV011

**Attachments:** None

Hello JCP Support,

I am preparing a DLA SBIR proposal for topic DLA26BZ03-NV011, due July 22, 2026 at 12:00 p.m. Eastern. My JCP account and organization were created successfully, but the organization status fields remain unavailable and the certification preflight does not populate the SAM details needed for review.

I have not submitted a JCP application and I am not claiming JCP certification. Could you please advise the fastest official step to synchronize the entity record and, if the prerequisites are complete, obtain an official application-submission receipt before the proposal deadline?

I will not transmit export-controlled technical information, credentials, or private entity identifiers by email. I can provide account or entity details through an official secure channel upon request.

Thank you,

Robert Ashworth

## Claim Boundary

This packet prepares one JCP portal-support request. It does not prove JCP application submission, DD Form 2345 certification, SAM or SPRS compliance, proposal submission, eligibility, or award status.

## Call Now

The official DLA Customer Interaction Center is listed as available
`24/7/365`. Call `1-877-352-2255`
and have the entity name and CAGE/NCAGE code ready to provide privately when
the agent asks. Do not put either value in this public packet.

Official source: https://www.dla.mil/logistics-operations/services/joint-certification-program/DLA/

### Script

Hello. I am calling for Joint Certification Program portal support for an organization preparing a DLA SBIR proposal for topic DLA26BZ03-NV011, due today at 12:00 p.m. Eastern.

My JCP account and organization were created successfully, but the organization status fields remain unavailable and the certification preflight does not populate the SAM details needed for review.

I have not submitted a JCP application and I am not claiming JCP certification. Can you tell me the fastest official step to synchronize the entity record and, if the prerequisites are complete, obtain an official application-submission receipt before the proposal deadline?

I have the entity name and CAGE or NCAGE code available to provide privately when you ask for them.

### Stop Rule

**Operator hard stop:** 2026-07-22 9:30 AM Central / 10:30 AM Eastern

Preserve a 90-minute review and portal buffer before the government deadline. If no official application-submission
receipt exists at that point, do not upload a substitute, certify Volume V, or
submit the proposal as though JCP were complete.

Prohibited substitutes:

- JCP organization-creation receipt
- portal screenshot without official application-submission status
- self-authored certification statement
