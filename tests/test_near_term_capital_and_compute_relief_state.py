import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "NEAR_TERM_CAPITAL_AND_COMPUTE_RELIEF_STATE_2026-07-23.json"
)
PACKET_PATH = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "NEAR_TERM_CAPITAL_AND_COMPUTE_RELIEF_PACKET_2026-07-23.md"
)


def load_state() -> dict:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def test_relief_routes_are_ranked_and_source_bound() -> None:
    state = load_state()
    routes = state["ranked_routes"]
    source_path = ROOT / state["official_source_evidence_path"]
    source_evidence = json.loads(source_path.read_text(encoding="utf-8"))
    sources = {
        row["source_evidence_id"]: row for row in source_evidence["sources"]
    }

    assert state["selected_investor_route"] == "third_sphere_seedstrap"
    assert state["selected_compute_route"] == "microsoft_for_startups_no_referral"
    assert state["source_refresh_required_before_new_external_action"] is True
    assert [route["priority"] for route in routes] == [1, 2, 3, 4]
    assert len({route["route_id"] for route in routes}) == len(routes)
    assert all(route["official_url"].startswith("https://") for route in routes)
    assert all(route["verified_utc"] == state["as_of_utc"] for route in routes)
    assert source_evidence["schema"] == (
        "lumencore.near_term_capital_compute_official_source_evidence.v1"
    )
    assert len(sources) == len(routes)
    for route in routes:
        source = sources[route["source_evidence_id"]]
        facts = source["reviewed_fact_snapshot"]
        assert source["route_id"] == route["route_id"]
        assert source["official_url"] == route["official_url"]
        assert source["http_status"] == 200
        assert len(source["content_sha256"]) == 64
        assert facts["published_value"] == route["published_value"]
        assert facts["published_timing"] == route["published_timing"]


def test_relief_routes_fail_closed_for_external_actions() -> None:
    state = load_state()

    assert state["send_now_count"] == 0
    assert state["portal_submit_now_count"] == 0
    assert all(
        route["external_action_policy"].startswith("FOUNDER_ONLY_")
        for route in state["ranked_routes"]
    )
    assert all(route["private_or_legal_gates"] for route in state["ranked_routes"])
    assert "guaranteed funding" in state["global_claim_boundary"]
    assert "payment information" in state["global_action_boundary"]
    third_sphere = next(
        route
        for route in state["ranked_routes"]
        if route["route_id"] == "third_sphere_seedstrap"
    )
    assert third_sphere["current_state"] == (
        "INITIAL_PUBLIC_SAFE_OUTREACH_SENT_PRIVATE_APPLICATION_FACTS_OPEN"
    )
    receipt_path = ROOT / third_sphere["send_receipt_path"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    send_receipt = receipt["receipt"]
    assert send_receipt["delivery_state"] == "SENT"
    assert receipt["controls"]["do_not_repeat_without_substantive_inbound"] is True
    canonical = "|".join(
        str(send_receipt[field])
        for field in (
            "lane_id",
            "template_id",
            "sent_utc",
            "recipient_route_sha256",
            "subject_sha256",
            "body_sha256",
            "gmail_message_id_sha256",
            "gmail_thread_id_sha256",
            "attachment_count",
            "cc_count",
            "bcc_count",
        )
    )
    assert send_receipt["sent_message_receipt_sha256"] == hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest().upper()


def test_relief_packet_preserves_claim_and_cost_boundaries() -> None:
    packet = PACKET_PATH.read_text(encoding="utf-8")

    assert "pre-revenue and pilot-stage" in packet
    assert "not field validation" in packet
    assert "automatically converts to pay-as-you-go" in packet
    assert "Do not guess or autofill these fields" in packet
    assert "https://thirdsphere.com/csp/" in packet
    assert "https://aws.amazon.com/startups/credits/" in packet
