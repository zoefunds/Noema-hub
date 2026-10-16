import ast
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).parents[2]
HUB = ROOT / "contracts" / "noema_hub.py"
WITNESS = ROOT / "contracts" / "source_witness.py"
ENGINE = ROOT / "contracts" / "verdict_engine.py"


def contract_methods(path: Path, class_name: str) -> set[str]:
    tree = ast.parse(path.read_text())
    contract = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    return {node.name for node in contract.body if isinstance(node, ast.FunctionDef)}


def test_hub_exposes_submission_and_economic_lifecycle():
    methods = contract_methods(HUB, "NoemaHub")
    assert {"open_dossier", "seal_disclosure", "disclose", "record_attestation", "record_verdict",
            "expire_disclosure", "expire_stage", "expire_dossier", "withdraw", "get_stats"} <= methods


def test_unavailable_http_callback_refunds_researcher_bond_and_marks_submission_retryable():
    tree = ast.parse(HUB.read_text())
    contract = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "NoemaHub")
    method = next(node for node in contract.body if isinstance(node, ast.FunctionDef) and node.name == "record_attestation")
    unavailable = next(node for node in ast.walk(method) if isinstance(node, ast.If)
                       and ast.unparse(node.test) == "result.get('status') == 'UNAVAILABLE'")
    body = "\n".join(ast.unparse(statement) for statement in unavailable.body)
    assert "submission['status'] = 'RETRYABLE'" in body
    assert "self._release_bond(submission, submission['researcher'])" in body
    assert "self._finish_submission(dossier, submission)" in body
    assert "dossier['sponsor']" not in body


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
    balance_guard = hub.index("if int(self.balance) < liabilities:")
    assert balance_guard < zero < transfer
    assert "Hub is underfunded; recapitalize before withdrawing" in hub
    assert zero < transfer
    assert "gl.transfer(" not in hub
    assert "@gl.evm.contract_interface" in hub
    assert "_EvmRecipient(Address(str(account))).emit_transfer" in hub
    assert "self.withdrawals[withdrawal_id]" in hub
    assert '"status": "PENDING"' in hub
    assert '"FAILED_RECREDITED"' in hub and '"DELIVERED"' in hub
    assert "self.pending_outbound[account]) + amount" in hub
    assert "def __on_errored_message__" in hub
    assert 'amount > expected' in hub
    assert "self._credit(account, amount)" in hub


def test_external_payout_failure_is_explicitly_not_claimed_as_recoverable():
    hub = HUB.read_text()
    verification = (ROOT / "docs" / "VERIFICATION.md").read_text()
    deployment = (ROOT / "docs" / "DEPLOYMENT.md").read_text()
    assert "EOA transfers are external EVM messages and do not call this hook" in hub
    assert "reconcile_withdrawal" in verification
    assert "FAILED_RECREDITED" in deployment


def test_payout_reconciliation_requires_exact_parent_child_receipt_linkage():
    tree = ast.parse(HUB.read_text())
    names = {"_tx_id", "_tx_value", "_tx_address", "_tx_timestamp", "_realized_payout_loss", "_payout_receipt_outcome"}
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {"WITHDRAW_CALLDATA": "DgZtZXRob2REd2l0aGRyYXc=", "datetime": datetime, "timezone": timezone}
    exec(compile(ast.Module(body=functions, type_ignores=[]), "payout_receipt_helpers", "exec"), namespace)
    recipient, hub = "0x" + "7" * 40, "0x" + "8" * 40
    parent_id, child_id = "0x" + "1" * 64, "0x" + "2" * 64
    parent = {"tx_id": parent_id, "status": "FINALIZED", "created_at": "2026-10-16T10:00:00.500000+00:00",
        "data": {"calldata": "DgZtZXRob2REd2l0aGRyYXc="}, "from_address": recipient,
        "to_address": hub, "triggered_transactions": [child_id],
        "messages": [{"recipient": recipient, "value": "0x3", "onAcceptance": False}]}
    child = {"tx_id": child_id, "status": "FINALIZED", "triggered_by": parent_id,
        "from_address": hub, "to_address": recipient, "value": "3", "value_credited": True}
    check = namespace["_payout_receipt_outcome"]
    args = (parent_id, child_id, hub, recipient, 3, "2026-10-16T10:00:00.500000+00:00")
    assert check(parent, child, *args) == "DELIVERED"
    assert check(parent, {**child, "value_credited": False}, *args) == "FAILED"
    assert check(parent, {**child, "value_credited": None}, *args) == "INVALID"
    assert check(parent, {**child, "triggered_by": "0x" + "3" * 64}, *args) == "INVALID"
    assert check(parent, {**child, "value": "0x4"}, *args) == "INVALID"
    assert check({**parent, "messages": []}, child, *args) == "INVALID"
    assert check({**parent, "triggered_transactions": []}, child, *args) == "DELIVERED"
    assert check({**parent, "created_at": "2026-10-15T10:00:00.500000+00:00"}, child, *args) == "INVALID"
    assert check({**parent, "data": {"calldata": "other-call"}}, child, *args) == "INVALID"
    assert check(parent, {**child, "status": "ACCEPTED"}, *args) == "PENDING"
    assert check(parent, child, "0x" + "4" * 64, child_id, hub, recipient, 3, args[-1]) == "INVALID"


def test_failed_payout_restoration_accounts_for_actual_backing_loss_only():
    tree = ast.parse(HUB.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_realized_payout_loss")
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "payout_loss_helper", "exec"), namespace)
    realized_loss = namespace["_realized_payout_loss"]
    amount = 1_100_000_000_000_000
    # The child failed and the GEN left Hub custody: restored claim is fully under-backed.
    assert realized_loss(amount, 0, amount, amount, 0) == amount
    # Runtime failure returned the GEN to the Hub: restore the claim without inventing a loss.
    assert realized_loss(amount, 0, amount, amount, amount) == 0
    # Existing shortfall is not charged a second time; only the new deficit delta counts.
    assert realized_loss(amount, 20, 0, amount + 20, 0) == amount


def test_bounds_and_timeout_rollback_are_explicit():
    hub = HUB.read_text()
    assert "MAX_LIFETIME_SUBMISSIONS = 72" in hub
    assert "MAX_EVIDENCE = 18" in hub
    assert 'item["id"] != submission["id"]' in hub
    assert '"INCONCLUSIVE_TIMEOUT"' in hub
