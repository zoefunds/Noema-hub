import ast
from pathlib import Path


ROOT = Path(__file__).parents[2]
HUB = ROOT / "contracts" / "noema_hub.py"
WITNESS = ROOT / "contracts" / "source_witness.py"
ENGINE = ROOT / "contracts" / "verdict_engine.py"


def contract_methods(path: Path, class_name: str) -> set[str]:
    tree = ast.parse(path.read_text())
    contract = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    return {node.name for node in contract.body if isinstance(node, ast.FunctionDef)}


def test_hub_exposes_complete_recovery_and_economic_lifecycle():
    methods = contract_methods(HUB, "NoemaHub")
    assert {"open_dossier", "seal_disclosure", "disclose", "record_attestation", "record_verdict",
            "expire_disclosure", "expire_stage", "expire_dossier", "withdraw", "get_stats"} <= methods


def test_workers_are_bound_and_callbacks_are_authenticated():
    hub = HUB.read_text()
    witness = WITNESS.read_text()
    engine = ENGINE.read_text()
    assert "witness callback only" in hub and "engine callback only" in hub
    assert "only the bound hub" in witness and "only the bound hub" in engine
    assert "self.bootstrapper = \"\"" in hub


def test_provenance_and_closure_consensus_fields_are_code_level_invariants():
    witness = WITNESS.read_text()
    engine = ENGINE.read_text()
    for field in ("content_digest", "http_status", "requested_origin", "verified_response_origin",
                  "transport_origin_verified", "document_publisher", "document_canonical_url"):
        assert field in witness
    for field in ("manifest_root", "decisive_ids", "basis_digest", "outcome", "sufficient",
                  "counterfactual_outcome", "contribution_required"):
        assert field in engine


def test_http_and_origin_provenance_are_enforced_before_semantic_acceptance():
    witness = WITNESS.read_text()
    assert "SUCCESS_STATUS_MIN <= status_code <= SUCCESS_STATUS_MAX" in witness
    assert 'parts.scheme != "https"' in witness
    assert "parts.username or parts.password" in witness
    assert '"transport_origin_verified": False' in witness
    assert 'answer["document_canonical_url"] = ""' in witness
    assert "TEMPORARY_HTTP_STATUSES" in witness
    assert 'return "UNAVAILABLE"' in witness
    assert 'classification = _classify_http_status(status_code)' in witness


def test_executable_settlement_requires_candidate_and_bounded_decisive_set():
    hub = HUB.read_text()
    engine = ENGINE.read_text()
    assert "MAX_DECISIVE_IDS = 12" in hub and "MAX_DECISIVE_IDS = 12" in engine
    assert 'submission["id"] not in decisive_ids' in hub
    assert 'result.get("counterfactual_outcome") != "UNRESOLVED"' in hub
    assert 'result.get("contribution_required") is not True' in hub
    assert "len(ids) > MAX_DECISIVE_IDS" in engine


def test_native_withdrawal_is_checks_effects_interactions_and_message_based():
    hub = HUB.read_text()
    assert "if not self.native_payouts_enabled" in hub
    assert "native payouts are unavailable on this deployment" in hub
    zero = hub.index("self.credits[account] = u256(0)")
    transfer = hub.index("_EvmRecipient(Address(str(account))).emit_transfer(value=u256(amount), on=\"finalized\")")
    assert zero < transfer
    assert "gl.transfer(" not in hub
    assert "@gl.evm.contract_interface" in hub
    assert "_EvmRecipient(Address(str(account))).emit_transfer" in hub
    assert "self.withdrawals[withdrawal_id]" in hub
    assert '"status": "PENDING"' in hub
    assert '"DELIVERY_REPORTED"' in hub
    assert "self.pending_outbound[account]) + amount" in hub
    assert "def __on_errored_message__" in hub
    assert 'amount > expected' in hub
    assert "self._credit(account, amount)" in hub


def test_bounds_and_timeout_rollback_are_explicit():
    hub = HUB.read_text()
    assert "MAX_LIFETIME_SUBMISSIONS = 72" in hub
    assert "MAX_EVIDENCE = 18" in hub
    assert 'item["id"] != submission["id"]' in hub
    assert '"INCONCLUSIVE_TIMEOUT"' in hub
