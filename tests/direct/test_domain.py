import json
import pytest

from contracts.domain import (
    MAX_EVIDENCE,
    MAX_LIFETIME_SUBMISSIONS,
    MAX_DECISIVE_IDS,
    commitment_for,
    evidence_key,
    manifest_root,
    normalize_url,
    validate_decision,
)


def record(index: int) -> dict:
    return {
        "id": f"note-{index}",
        "claim_digest": f"{index:064x}",
        "content_digest": f"{index + 100:064x}",
        "source_host": "records.example.org",
    }


def test_url_normalization_removes_fragment_and_default_port():
    assert normalize_url("https://EXAMPLE.org:443//public/item?q=1#section") == "https://example.org/public/item?q=1"


@pytest.mark.parametrize("url", ["http://example.org", "https://user:pass@example.org", "ftp://example.org/a"])
def test_url_policy_rejects_unsafe_shapes(url):
    with pytest.raises(ValueError):
        normalize_url(url)


def test_commitment_is_domain_bound_to_chain_hub_case_and_researcher():
    base = dict(chain_id="61999", hub="0x" + "1" * 40, dossier_id="noema-1",
                researcher="0x" + "2" * 40, url="https://example.org/a", claim="Release shipped", salt="ab" * 32)
    expected = commitment_for(**base)
    assert expected == commitment_for(**base)
    for key, changed in (("chain_id", "1"), ("dossier_id", "noema-2"),
                         ("researcher", "0x" + "3" * 40), ("salt", "cd" * 32)):
        assert commitment_for(**{**base, key: changed}) != expected


def test_evidence_reservation_binds_normalized_url_and_claim():
    first = evidence_key("noema-1", "https://EXAMPLE.org:443/a#x", "A material fact")
    assert first == evidence_key("noema-1", "https://example.org/a", "A material fact")
    assert first != evidence_key("noema-1", "https://example.org/a", "A different fact")


def test_manifest_root_is_order_and_provenance_sensitive():
    items = [record(1), record(2), record(3)]
    root = manifest_root(items)
    assert root != manifest_root(list(reversed(items)))
    altered = json.loads(json.dumps(items))
    altered[1]["content_digest"] = "f" * 64
    assert root != manifest_root(altered)


def test_manifest_root_matches_published_studionet_vector():
    records = [
        {"id": "base-1", "claim_digest": "298eb98ab840effe4ed8c1381e5a44948e91ff015acb4bd5c1291b1add83c393",
         "content_digest": "ba4e1f69ff48386e72a9c5e1edaf76aad64a475c2d51af79ccba6d1128261ba7",
         "source_host": "raw.githubusercontent.com"},
        {"id": "note-1", "claim_digest": "e0eba3612db9a6c80d2040c007bf37ef83ef0a3e5d9ed1b107494c64332e961b",
         "content_digest": "d17f227e4df5da1600391338865ce0f3055211760a36688f816941d58232d8dc",
         "source_host": "raw.githubusercontent.com"},
    ]
    assert manifest_root(records) == "9f18409690f81c54c257d64c0e15572e7c77674afa5c7707de57e4411c87f000"


def test_resolved_decision_requires_valid_unique_decisive_ids_and_basis():
    result = validate_decision({"outcome": "POSITION_A", "decisive_ids": ["base-1", "note-4"],
                                "basis": "Together these records satisfy both clauses."}, {"base-1", "note-4"})
    assert result["outcome"] == "POSITION_A"
    with pytest.raises(ValueError):
        validate_decision({"outcome": "POSITION_A", "decisive_ids": [], "basis": "x"}, {"base-1"})
    with pytest.raises(ValueError):
        validate_decision({"outcome": "UNRESOLVED", "decisive_ids": ["base-1"], "basis": "x"}, {"base-1"})


def test_candidate_independent_verdict_cannot_receive_reward():
    with pytest.raises(ValueError, match="current candidate"):
        validate_decision({"outcome": "POSITION_A", "decisive_ids": ["base-1"],
                           "counterfactual_outcome": "POSITION_A", "basis": "Baseline alone."},
                          {"base-1", "note-4"}, candidate_id="note-4")
    with pytest.raises(ValueError, match="unresolved without"):
        validate_decision({"outcome": "POSITION_A", "decisive_ids": ["base-1", "note-4"],
                           "counterfactual_outcome": "POSITION_A", "basis": "Candidate is redundant."},
                          {"base-1", "note-4"}, candidate_id="note-4")


def test_oversized_decisive_set_is_rejected():
    ids = {f"note-{index}" for index in range(MAX_DECISIVE_IDS + 1)}
    with pytest.raises(ValueError, match="invalid decisive ids"):
        validate_decision({"outcome": "POSITION_A", "decisive_ids": sorted(ids),
                           "basis": "Too many records."}, ids)


def test_large_graph_has_hard_cumulative_bounds():
    retained = [record(index) for index in range(MAX_EVIDENCE)]
    submissions = [f"note-{index}" for index in range(MAX_LIFETIME_SUBMISSIONS)]
    assert len(retained) == 18
    assert len(submissions) == 72
    assert len(manifest_root(retained)) == 64
    assert MAX_LIFETIME_SUBMISSIONS > MAX_EVIDENCE
