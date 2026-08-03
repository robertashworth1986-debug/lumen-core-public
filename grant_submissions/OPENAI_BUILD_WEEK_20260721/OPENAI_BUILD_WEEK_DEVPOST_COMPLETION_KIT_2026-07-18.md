# OpenAI Build Week - Devpost Completion Kit

Deadline: `2026-07-21T19:00:00-05:00` (`2026-07-22T00:00:00Z`)
Observed portal state: `SIGNED_IN_AT_OBSERVATION` / `REGISTERED_CONFIRMED` / `DRAFT_2_OF_5_CONFIRMED` / `NONE_OBSERVED`
Base readiness: `5/10` gates pass. Verified portal progress raises effective readiness to `6/10`; final submission remains blocked.

## Field Registry

| Step | Field | Portal Label | Exact? | Required | State |
|---|---|---|---|---|---|
| 1_manage_team | `team_members` | Teammates | `true` | `false` | `OPTIONAL_NOT_SELECTED` |
| 2_project_overview | `project_name` | Project name | `true` | `true` | `SOURCE_BACKED_READY` |
| 2_project_overview | `project_tagline` | Project tagline | `true` | `true` | `SOURCE_BACKED_READY` |
| 2_project_overview | `thumbnail_image` | Thumbnail image for the Project Gallery | `true` | `true` | `SOURCE_BACKED_LOCAL_UPLOAD_READY_PUBLICATION_OPEN` |
| 3_project_details | `project_story` | Project story | `true` | `true` | `SOURCE_BACKED_READY_FINAL_PREVIEW_RECHECK_REQUIRED` |
| 3_project_details | `built_with_tags` | Built with tags | `true` | `true` | `SOURCE_BACKED_READY_FINAL_PREVIEW_RECHECK_REQUIRED` |
| 3_project_details | `try_it_out_link` | Try it Out links | `true` | `true` | `SOURCE_BACKED_READY_FINAL_PREVIEW_RECHECK_REQUIRED` |
| 3_project_details | `image_gallery` | Image Gallery | `true` | `false` | `OPTIONAL_PRIVACY_REVIEW_OPEN` |
| 3_project_details | `video_demo_link` | Video demo link | `true` | `true` | `LOCAL_VIDEO_VERIFIED_PUBLICATION_OPEN` |
| 4_additional_details | `submitter_type` | Submitter Type | `true` | `true` | `MISSING_HUMAN_LEGAL_INPUT` |
| 4_additional_details | `country_of_residence` | Countries of Residence | `true` | `true` | `MISSING_PRIVATE_HUMAN_INPUT` |
| 4_additional_details | `category` | unobserved custom label | `false` | `true` | `SOURCE_BACKED_READY_PORTAL_LABEL_UNOBSERVED` |
| 4_additional_details | `repository_url` | unobserved custom label | `false` | `true` | `SOURCE_BACKED_READY_EXTERNAL_ACCESS_RECHECK_REQUIRED` |
| 4_additional_details | `repository_license` | unobserved custom label | `false` | `true` | `SOURCE_BACKED_READY_HUMAN_REPRESENTATION_REQUIRED` |
| 4_additional_details | `new_or_existing_project` | unobserved custom label | `false` | `true` | `SOURCE_BACKED_READY_PORTAL_LABEL_UNOBSERVED` |
| 4_additional_details | `hackathon_improvement_explanation` | unobserved custom label | `false` | `true` | `SOURCE_BACKED_READY_PORTAL_LABEL_UNOBSERVED` |
| 4_additional_details | `confirmed_model_identity` | unobserved custom label | `false` | `true` | `SOURCE_BACKED_READY_PORTAL_LABEL_UNOBSERVED` |
| 4_additional_details | `feedback_session_id` | unobserved custom label | `false` | `true` | `MISSING_FEEDBACK_SESSION_ID` |
| 4_additional_details | `representative_authorization` | unobserved custom label | `false` | `true` | `MISSING_CONDITIONAL_LEGAL_ATTESTATION` |
| 5_submit | `official_rules_and_terms` | Agree to the hackathon terms and conditions | `true` | `true` | `HUMAN_LEGAL_ACCEPTANCE_REQUIRED` |
| 5_submit | `final_submit_action` | Submit project | `true` | `true` | `FINAL_HUMAN_ACTION_BLOCKED` |

## Public Demo Checklist

- `PASS_OBSERVED` - All ten required public files returned HTTP 200 and matched local SHA-256 identities at the recorded observation.
- `PASS_OBSERVED` - Desktop and mobile browser QA records are integrity-valid and recorded no horizontal overflow.
- `OPEN_FINAL_PREVIEW_RECHECK` - Load the demo and repository from a signed-out browser without credentials or private identifiers.
- `OPEN_FUTURE_AVAILABILITY_NOT_PROVABLE` - Confirm the free demo will remain available without restriction through the judging period.
- `OPEN_FINAL_PREVIEW_RECHECK` - Verify the public behavior matches the submitted story and video, including the HOLD decision.

## Video Checklist

- `DRAFT_PRESENT_RECORDING_OPEN` - Use the bounded demo script and keep the final cut shorter than 180 seconds.
- `OPEN_RECORDING_REQUIRED` - Show the live receipt load, 4/4 artifact verification, HOLD decision, tamper failure, and blocked promotion.
- `BLOCKED_MODEL_PROVENANCE_MISSING` - Audio must accurately explain how Codex and the directly confirmed required model were used.
- `OPEN_PRIVACY_IP_REVIEW` - Exclude unlicensed music, third-party trademarks, private screens, credentials, and patent-sensitive material.
- `OPEN_PUBLICATION_REQUIRED` - Upload to YouTube, make it public and embeddable, then verify playback while signed out.

## Privacy/IP Checklist

- `HUMAN_REVIEW_REQUIRED` - No passwords, API keys, OTPs, cookies, private portal identifiers, or meeting credentials appear in any artifact.
- `HUMAN_REVIEW_REQUIRED` - No private addresses, phone numbers, tax identifiers, signatures, or unrelated personal data are published.
- `HUMAN_REVIEW_REQUIRED` - No unpublished claim language, private patent drafts, CUI/export-controlled material, or grant-portal screenshots are disclosed.
- `HUMAN_LEGAL_REVIEW_REQUIRED` - Entrant confirms original ownership, third-party permissions, and open-source license compliance.
- `HUMAN_LEGAL_REVIEW_REQUIRED` - Entrant reviews the non-exclusive judging license and the publicity use of name, likeness, voice, and image before acceptance.
- `HUMAN_REVIEW_REQUIRED` - Every performance statement is traceable to the recorded receipt and preserves time-bounded observation language.

## Hard Stop Conditions

- Challenge registration and a two-of-five project draft are confirmed; no final submission confirmation exists.
- Project details and additional information remain incomplete.
- The `/feedback` Session ID is not present.
- A verified local under-three-minute demo exists, but no public YouTube URL is recorded.
- Entrant type, residence, representative authority, rules, publicity/IP terms, and final certification require human review.
- Contest-specific portal labels must be captured from the joined form before field population is called exact.

## Actions Not Authorized By This Kit

- `authenticate`
- `join_or_register`
- `create_or_import_project`
- `upload_file_or_video`
- `publish`
- `accept_terms`
- `certify`
- `submit`
- `contact_anyone`

## Claim Boundary

This kit prepares source-backed draft content and a field-by-field completion contract. It confirms a bounded project draft and locally verified release assets. It does not prove a /feedback Session ID, eligibility, ownership, legal acceptance, video publication, final submission, judging outcome, endorsement, award, external validation, patent rights, safety, funding, or value.
