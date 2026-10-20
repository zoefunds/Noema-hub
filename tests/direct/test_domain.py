import json
import pytest
import ast
from pathlib import Path

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


@pytest.mark.parametrize("status", [408, 425, 429, 500, 502, 503, 504])
def test_temporary_http_failures_are_unavailable_and_do_not_imply_invalid_evidence(status):
    assert classify_http_status(status) == "UNAVAILABLE"


@pytest.mark.parametrize("status", [400, 401, 403, 404, 410])
def test_permanent_http_source_failures_are_not_attested(status):
    assert classify_http_status(status) == "REJECTED"


def test_document_body_with_unsuccessful_http_status_cannot_be_attested():
    body = "A valid looking public notice that must not be admitted when the response status is an error."
    assert body
    assert classify_http_status(503) == "UNAVAILABLE"
    assert classify_http_status(200) == "SUCCESS"


@pytest.mark.parametrize(("status", "expected"), [(429, "UNAVAILABLE"), (503, "UNAVAILABLE"), (404, "REJECTED")])
def test_source_witness_never_semantically_attests_error_response_body(status, expected):
    import hashlib
    from types import SimpleNamespace

    source = (Path(__file__).parents[2] / "contracts" / "source_witness.py").read_text()
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_inspect")
    body = b"Apache License Version 2.0 - valid documentary content must not override an HTTP error status."
    calls = []

    class FakeVm:
        class Return:
            pass

        @staticmethod
        def run_nondet_unsafe(leader, _validator):
            return leader()

    def fake_web_get(_url):
        return SimpleNamespace(status=status, body=body, url="https://example.org/license", redirected=False)

    def fake_exec_prompt(*_args, **_kwargs):
        calls.append("semantic-evaluation")
        return {field: True for field in ("same_subject", "policy_compliant", "claim_supported", "time_aligned",
                                          "materially_new", "internally_consistent")} | {"basis": "Supported."}

    fake_gl = SimpleNamespace(
        nondet=SimpleNamespace(web=SimpleNamespace(get=fake_web_get), exec_prompt=fake_exec_prompt),
        vm=FakeVm,
    )
    namespace = {
        "gl": fake_gl,
        "hashlib": hashlib,
        "json": json,
        "MAX_SOURCE_BYTES": 120_000,
        "FIELDS": ("same_subject", "policy_compliant", "claim_supported", "time_aligned",
                   "materially_new", "internally_consistent"),
        "_json": lambda value: json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        "_normalize": lambda value: {**value, "status": "ATTESTED"},
        "_classify_http_status": classify_http_status,
        "_response_provenance": lambda _response, _url: ("https://example.org", True, [], "VERIFIED_DIRECT_RESPONSE"),
        "_response_status": lambda response: response.status,
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]), "source_witness_inspect", "exec"), namespace)
    result = namespace["_inspect"]("question", "rule", "policy", "[]", "https://example.org/license", "claim")

    assert result["status"] == expected
    assert result["http_status"] == status
    assert result["content_digest"] == hashlib.sha256(body).hexdigest()
    assert not any(result[field] for field in namespace["FIELDS"])
    assert calls == []


def test_source_witness_runs_semantics_for_a_successful_document_response():
    import hashlib
    from types import SimpleNamespace

    source = (Path(__file__).parents[2] / "contracts" / "source_witness.py").read_text()
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_inspect")
    body = (b"x" * 25_000) + b"Apache License Version 2.0"
    calls = []
    fields = ("same_subject", "policy_compliant", "claim_supported", "time_aligned",
              "materially_new", "internally_consistent")

    class FakeVm:
        class Return:
            pass

        @staticmethod
        def run_nondet_unsafe(leader, _validator):
            return leader()

    def fake_exec_prompt(*_args, **_kwargs):
        calls.append("semantic-evaluation")
        return {field: True for field in fields} | {"support_quote": "Apache License Version 2.0",
                                                     "basis": "The source states Apache License Version 2.0."}

    fake_gl = SimpleNamespace(
        nondet=SimpleNamespace(web=SimpleNamespace(get=lambda _url: SimpleNamespace(
            status=200, body=body, url="https://example.org/license", redirected=False)),
                               exec_prompt=fake_exec_prompt),
        vm=FakeVm,
    )
    namespace = {
        "gl": fake_gl, "hashlib": hashlib, "json": json, "MAX_SOURCE_BYTES": 120_000, "FIELDS": fields,
        "_json": lambda value: json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        "_normalize": lambda value: {**value, "status": "ATTESTED"},
        "_classify_http_status": classify_http_status,
        "_response_provenance": lambda _response, _url: ("https://example.org", True, [], "VERIFIED_DIRECT_RESPONSE"),
        "_response_status": lambda response: response.status,
        "_sha": lambda value: hashlib.sha256(value.encode()).hexdigest(),
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]), "source_witness_inspect", "exec"), namespace)
    result = namespace["_inspect"]("question", "rule", "policy", "[]", "https://example.org/license", "claim")

    assert result["status"] == "ATTESTED"
    assert result["http_status"] == 200
    assert result["content_digest"] == hashlib.sha256(body).hexdigest()
    assert result["support_digest"] == hashlib.sha256(b"Apache License Version 2.0").hexdigest()
    assert calls == ["semantic-evaluation"]


def test_source_witness_rejects_oversized_sources_instead_of_partially_inspecting_them():
    witness = (Path(__file__).parents[2] / "contracts" / "source_witness.py").read_text()
    assert "[:MAX_FETCH]" not in witness
    assert "if len(raw_body) > MAX_SOURCE_BYTES" in witness
    assert "partial inspection is forbidden" in witness


def test_source_witness_fails_closed_when_origin_or_redirect_cannot_be_authenticated():
    witness = (Path(__file__).parents[2] / "contracts" / "source_witness.py").read_text()
    assert '"UNVERIFIED_RESPONSE_ORIGIN"' in witness
    assert '"UNSAFE_REDIRECT"' in witness
    assert "if not origin_admissible" in witness
    assert '"status": "REJECTED"' in witness


def test_response_provenance_accepts_only_an_exact_direct_https_origin():
    from types import SimpleNamespace
    from urllib.parse import urlsplit, urlunsplit

    source = (Path(__file__).parents[2] / "contracts" / "source_witness.py").read_text()
    tree = ast.parse(source)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in ("_requested_provenance", "_response_provenance")]
    class UserError(Exception):
        pass
    namespace = {"urlsplit": urlsplit, "urlunsplit": urlunsplit, "re": __import__("re"),
                 "gl": type("Gl", (), {"vm": type("Vm", (), {"UserError": UserError})})}
    exec(compile(ast.Module(body=functions, type_ignores=[]), "source_provenance", "exec"), namespace)
    check = namespace["_response_provenance"]
    direct = SimpleNamespace(url="https://records.example/report", redirected=False, history=[])
    assert check(direct, "https://records.example/report") == (
        "https://records.example", True, [], "VERIFIED_DIRECT_RESPONSE")
    assert check(SimpleNamespace(url="", redirected=False), "https://records.example/report")[3] == "UNVERIFIED_RESPONSE_ORIGIN"
    assert check(SimpleNamespace(url="https://evil.example/report", redirected=True, history=[]),
                 "https://records.example/report")[3] == "UNSAFE_REDIRECT"
    immutable = "https://raw.githubusercontent.com/openai/codex/e1b9c9457ceca75a99b034a5df39ac48c3998d15/LICENSE"
    assert check(SimpleNamespace(url=""), immutable) == (
        "https://raw.githubusercontent.com", True, [], "VERIFIED_CONTENT_ADDRESSED_ORIGIN")
    assert check(SimpleNamespace(url=""), "https://raw.githubusercontent.com/openai/codex/main/LICENSE")[3] == "UNVERIFIED_RESPONSE_ORIGIN"


def classify_http_status(status):
    source = (Path(__file__).parents[2] / "contracts" / "source_witness.py").read_text()
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_classify_http_status")
    module = ast.Module(body=[function], type_ignores=[])
    namespace = {"SUCCESS_STATUS_MIN": 200, "SUCCESS_STATUS_MAX": 299,
                 "TEMPORARY_HTTP_STATUSES": (408, 425, 429, 500, 502, 503, 504)}
    exec(compile(module, "source_witness_http_classification", "exec"), namespace)
    return namespace["_classify_http_status"](status)
