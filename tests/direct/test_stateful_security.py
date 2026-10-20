import hashlib
import json


HUB = "contracts/noema_hub.py"
ENGINE = "contracts/verdict_engine.py"
WITNESS = "contracts/source_witness.py"


def _address(byte: str) -> str:
    return "0x" + byte * 40


def _base_dossier(sponsor: str, researcher: str) -> dict:
    return {
        "id": "noema-stateful",
        "sponsor": sponsor,
        "status": "OPEN",
        "reward_atto": "1000",
        "rules_root": "a" * 64,
        "manifest_root": "b" * 64,
        "evidence": [{"id": "note-1"}],
        "active_ids": ["note-1"],
        "queue": ["note-1"],
        "pending_id": "note-1",
        "stage_deadline": "100",
        "next_queue_position": 2,
        "submission_ids": ["note-1"],
    }


def _submission(researcher: str, status: str = "VERDICT_PENDING") -> dict:
    return {
        "id": "note-1",
        "dossier_id": "noema-stateful",
        "researcher": researcher,
        "status": status,
        "bond_atto": "100",
        "bond_released": False,
    }


def _evidence(evidence_id: str) -> dict:
    return {
        "id": evidence_id,
        "kind": "RESEARCH",
        "requested_url": "https://example.test/source",
        "requested_origin": "https://example.test",
        "claim_digest": "1" * 64,
        "content_digest": "2" * 64,
        "support_digest": "3" * 64,
        "source_size": 128,
        "http_status": 200,
        "verified_response_origin": "https://example.test",
        "transport_origin_verified": True,
        "provenance_status": "VERIFIED_DIRECT_RESPONSE",
    }


def test_witness_rejects_non_literal_values_for_every_admissibility_boolean(direct_deploy):
    witness = direct_deploy(WITNESS, _address("9"))
    normalize = witness._instance.attest.__globals__["_normalize"]
    valid = {name: True for name in witness._instance.attest.__globals__["FIELDS"]}
    valid.update({"basis": "All checks passed.", "support_quote": "verbatim"})
    assert normalize(valid)["status"] == "ATTESTED"
    for field in witness._instance.attest.__globals__["FIELDS"]:
        for malformed in (1, "true", {"value": True}):
            with __import__("pytest").raises(Exception, match="literal boolean"):
                normalize({**valid, field: malformed})


def test_conflicting_authenticated_quotes_execute_consensus_as_unresolved(
    direct_vm, direct_deploy
):
    """Run the actual VerdictEngine decision and its independent validator."""
    engine = direct_deploy(ENGINE, _address("9"))
    decide = engine._instance.resolve.__globals__["_decide"]
    manifest = [
        {**_evidence("evidence-red"), "support_quote": "The beacon is RED."},
        {**_evidence("evidence-blue"), "support_quote": "The beacon is BLUE."},
    ]
    direct_vm.mock_llm("NOEMA_VERDICT_ENGINE_V3", json.dumps({
        "outcome": "UNRESOLVED", "decisive_ids": [],
        "basis": "The authenticated support passages conflict on the beacon state required by the rule."
    }))
    result = decide(
        "What is the beacon state?",
        "Resolve only when two authenticated sources agree; conflicts are unresolved.",
        "RED", "BLUE", "a" * 64, json.dumps(manifest), "evidence-blue"
    )
    assert result["outcome"] == "UNRESOLVED"
    assert result["decisive_ids"] == []
    assert result["contribution_required"] is False
    assert "frozen rule" in result["basis"]
    assert result["manifest_root"] in result["basis"]
    # The validator re-executes the same source-bound prompt and must agree.
    assert direct_vm.run_validator(index=-2) is True
    assert direct_vm.run_validator(index=-1) is True


def test_resolved_basis_is_deterministically_bound_to_authenticated_support(direct_deploy):
    engine = direct_deploy(ENGINE, _address("9"))
    normalize = engine._instance.resolve.__globals__["_normalize"]
    evidence = _evidence("note-1")
    result = normalize({"outcome": "POSITION_A", "decisive_ids": ["note-1"],
                        "basis": "untrusted model prose"}, {"note-1": evidence}, "a" * 64, "b" * 64)
    assert "untrusted model prose" not in result["basis"]
    assert evidence["verified_response_origin"] in result["basis"]
    assert evidence["support_digest"] in result["basis"]
    assert result["basis_digest"] == hashlib.sha256(result["basis"].encode()).hexdigest()


def test_conflicting_evidence_consensus_is_economically_non_decisive(
    direct_vm, direct_deploy
):
    """Execute the real Hub callback for a conflict-consensus UNRESOLVED result."""
    sponsor, researcher, engine = _address("1"), _address("2"), _address("3")
    hub = direct_deploy(HUB, "", "", True)
    hub.engine_address = engine
    hub.configured = True
    hub.reward_escrow = 1000
    hub.bond_escrow = 100
    dossier = _base_dossier(sponsor, researcher)
    submission = _submission(researcher)
    hub.dossiers[dossier["id"]] = json.dumps(dossier)
    hub.submissions[submission["id"]] = json.dumps(submission)

    direct_vm.sender = bytes.fromhex(engine[2:])
    result = {
        "outcome": "UNRESOLVED",
        "sufficient": False,
        "decisive_ids": [],
        "basis": "Authenticated sources conflict on the required fact.",
        "basis_digest": "c" * 64,
        "rules_root": dossier["rules_root"],
        "manifest_root": dossier["manifest_root"],
        "counterfactual_outcome": "UNRESOLVED",
        "contribution_required": False,
    }
    hub.record_verdict("note-1", json.dumps(result))

    final_dossier = hub.get_dossier(dossier["id"])
    final_submission = hub.get_submission("note-1")
    assert final_submission["status"] == "ATTESTED_NON_DECISIVE"
    assert final_submission["verdict"]["basis"].startswith("Authenticated sources conflict")
    assert final_dossier["status"] == "OPEN"
    assert not final_dossier.get("winner")
    assert final_dossier["reward_atto"] == "1000"
    assert int(hub.reward_escrow) == 1000
    assert int(hub.bond_escrow) == 0
    assert hub.get_credit(researcher) == "100"


def test_verdict_timeout_rolls_back_candidate_and_restores_researcher_bond(
    direct_vm, direct_deploy
):
    sponsor, researcher = _address("1"), _address("2")
    hub = direct_deploy(HUB, "", "", True)
    hub.reward_escrow = 1000
    hub.bond_escrow = 100
    dossier = _base_dossier(sponsor, researcher)
    dossier["stage_deadline"] = "100"
    dossier["evidence"] = [_evidence("baseline-1"), _evidence("note-1")]
    submission = _submission(researcher)
    hub.dossiers[dossier["id"]] = json.dumps(dossier)
    hub.submissions[submission["id"]] = json.dumps(submission)

    direct_vm.warp("1970-01-01T00:01:41Z")
    hub.expire_stage(dossier["id"])

    final_dossier = hub.get_dossier(dossier["id"])
    final_submission = hub.get_submission("note-1")
    assert final_submission["status"] == "INCONCLUSIVE_TIMEOUT"
    assert [item["id"] for item in final_dossier["evidence"]] == ["baseline-1"]
    assert final_dossier["pending_id"] == ""
    assert final_dossier["reward_atto"] == "1000"
    assert int(hub.reward_escrow) == 1000
    assert int(hub.bond_escrow) == 0
    assert hub.get_credit(researcher) == "100"


def test_failed_receipt_recredits_once_and_receipt_replay_cannot_duplicate_credit(
    direct_vm, direct_deploy
):
    recipient = _address("4")
    parent_tx, child_tx = "0x" + "5" * 64, "0x" + "6" * 64
    hub = direct_deploy(HUB, "", "", True)
    # Address is loaded from the contract SDK; construct it via the module global.
    address = hub._instance.reconcile_withdrawal.__globals__["Address"](recipient)
    withdrawal_id = hashlib.sha256(b"stateful-withdrawal").hexdigest()
    receipt_key = hashlib.sha256((parent_tx + ":" + child_tx).encode()).hexdigest()
    item = {"id": withdrawal_id, "recipient": recipient, "amount": "300", "status": "PENDING",
            "created_at": "2026-10-20T00:00:00+00:00", "parent_tx": "", "child_tx": ""}
    hub.withdrawals[withdrawal_id] = json.dumps(item)
    hub.pending_outbound[address] = 300
    hub.pending_outbound_total = 300
    hub.withdrawn = 300
    direct_vm.deal(direct_vm._contract_address, 0)

    globals_ = hub._instance.reconcile_withdrawal.__globals__
    original = globals_["_verify_payout_receipts"]
    globals_["_verify_payout_receipts"] = lambda *args: {
        "outcome": "FAILED", "parent_id": parent_tx, "child_id": child_tx,
        "recipient": recipient, "amount": "300", "withdrawal_created_at": item["created_at"]}
    try:
        hub.reconcile_withdrawal(withdrawal_id, parent_tx, child_tx)
        assert hub.get_withdrawal(withdrawal_id)["status"] == "FAILED_RECREDITED"
        assert hub.get_credit(recipient) == "300"
        assert int(hub.pending_outbound_total) == 0
        assert hub.consumed_payout_receipts[receipt_key] == withdrawal_id

        with direct_vm.expect_revert("withdrawal is not pending"):
            hub.reconcile_withdrawal(withdrawal_id, parent_tx, child_tx)
        assert hub.get_credit(recipient) == "300"

        second_id = hashlib.sha256(b"second-withdrawal").hexdigest()
        hub.withdrawals[second_id] = json.dumps({**item, "id": second_id})
        hub.pending_outbound[address] = 300
        hub.pending_outbound_total = 300
        with direct_vm.expect_revert("payout receipt pair already consumed"):
            hub.reconcile_withdrawal(second_id, parent_tx, child_tx)
        assert hub.get_credit(recipient) == "300"
    finally:
        globals_["_verify_payout_receipts"] = original


def _pending_withdrawal(hub, direct_vm, recipient, amount):
    """Seed a PENDING withdrawal directly, mirroring what withdraw() produces."""
    address = hub._instance.reconcile_withdrawal.__globals__["Address"](recipient)
    withdrawal_id = hashlib.sha256((recipient + str(amount)).encode()).hexdigest()
    item = {"id": withdrawal_id, "recipient": recipient, "amount": str(amount), "status": "PENDING",
            "created_at": "2026-10-20T00:00:00+00:00", "parent_tx": "", "child_tx": ""}
    hub.withdrawals[withdrawal_id] = json.dumps(item)
    hub.pending_outbound[address] = amount
    hub.pending_outbound_total = amount
    hub.withdrawn = amount
    direct_vm.deal(direct_vm._contract_address, 0)
    return withdrawal_id, item


def test_delivered_receipt_settles_withdrawal_without_recrediting(direct_vm, direct_deploy):
    """A genuinely successful payout must clear pending_outbound and never touch credits."""
    recipient = _address("4")
    parent_tx, child_tx = "0x" + "7" * 64, "0x" + "8" * 64
    hub = direct_deploy(HUB, "", "", True)
    withdrawal_id, item = _pending_withdrawal(hub, direct_vm, recipient, 500)
    receipt_key = hashlib.sha256((parent_tx + ":" + child_tx).encode()).hexdigest()

    globals_ = hub._instance.reconcile_withdrawal.__globals__
    original = globals_["_verify_payout_receipts"]
    globals_["_verify_payout_receipts"] = lambda *args: {
        "outcome": "DELIVERED", "parent_id": parent_tx, "child_id": child_tx,
        "recipient": recipient, "amount": "500", "withdrawal_created_at": item["created_at"]}
    try:
        hub.reconcile_withdrawal(withdrawal_id, parent_tx, child_tx)
        assert hub.get_withdrawal(withdrawal_id)["status"] == "DELIVERED"
        assert hub.get_credit(recipient) == "0"
        assert int(hub.pending_outbound_total) == 0
        assert hub.get_pending_outbound(recipient) == "0"
        assert hub.consumed_payout_receipts[receipt_key] == withdrawal_id
        assert int(hub.withdrawn) == 500
    finally:
        globals_["_verify_payout_receipts"] = original


def test_forged_or_mismatched_receipt_is_rejected_and_leaves_state_unchanged(direct_vm, direct_deploy):
    """A receipt pair that fails consensus linkage must not settle or consume anything."""
    recipient = _address("4")
    parent_tx, child_tx = "0x" + "9" * 64, "0x" + "a" * 64
    hub = direct_deploy(HUB, "", "", True)
    withdrawal_id, _ = _pending_withdrawal(hub, direct_vm, recipient, 500)
    receipt_key = hashlib.sha256((parent_tx + ":" + child_tx).encode()).hexdigest()

    globals_ = hub._instance.reconcile_withdrawal.__globals__
    original = globals_["_verify_payout_receipts"]
    globals_["_verify_payout_receipts"] = lambda *args: {
        "outcome": "INVALID", "parent_id": parent_tx, "child_id": child_tx,
        "recipient": recipient, "amount": "500", "withdrawal_created_at": "2026-10-20T00:00:00+00:00"}
    try:
        with direct_vm.expect_revert("payout receipts do not match this withdrawal"):
            hub.reconcile_withdrawal(withdrawal_id, parent_tx, child_tx)
        assert hub.get_withdrawal(withdrawal_id)["status"] == "PENDING"
        assert hub.get_credit(recipient) == "0"
        assert hub.get_pending_outbound(recipient) == "500"
        assert int(hub.pending_outbound_total) == 500
        assert receipt_key not in hub.consumed_payout_receipts
    finally:
        globals_["_verify_payout_receipts"] = original


def test_unfinalized_receipt_is_rejected_without_mutating_state(direct_vm, direct_deploy):
    """A child that has not finalized yet must stay retryable, not fail closed into loss."""
    recipient = _address("4")
    parent_tx, child_tx = "0x" + "b" * 64, "0x" + "c" * 64
    hub = direct_deploy(HUB, "", "", True)
    withdrawal_id, _ = _pending_withdrawal(hub, direct_vm, recipient, 500)
    receipt_key = hashlib.sha256((parent_tx + ":" + child_tx).encode()).hexdigest()

    globals_ = hub._instance.reconcile_withdrawal.__globals__
    original = globals_["_verify_payout_receipts"]
    globals_["_verify_payout_receipts"] = lambda *args: {
        "outcome": "PENDING", "parent_id": parent_tx, "child_id": child_tx,
        "recipient": recipient, "amount": "500", "withdrawal_created_at": "2026-10-20T00:00:00+00:00"}
    try:
        with direct_vm.expect_revert("payout child is not finalized"):
            hub.reconcile_withdrawal(withdrawal_id, parent_tx, child_tx)
        assert hub.get_withdrawal(withdrawal_id)["status"] == "PENDING"
        assert hub.get_pending_outbound(recipient) == "500"
        assert receipt_key not in hub.consumed_payout_receipts
    finally:
        globals_["_verify_payout_receipts"] = original


def test_unavailable_rpc_lookup_is_rejected_without_mutating_state(direct_vm, direct_deploy):
    """A StudioNet RPC read failure must be retryable, never silently treated as settled."""
    recipient = _address("4")
    parent_tx, child_tx = "0x" + "d" * 64, "0x" + "e" * 64
    hub = direct_deploy(HUB, "", "", True)
    withdrawal_id, _ = _pending_withdrawal(hub, direct_vm, recipient, 500)
    receipt_key = hashlib.sha256((parent_tx + ":" + child_tx).encode()).hexdigest()

    globals_ = hub._instance.reconcile_withdrawal.__globals__
    original = globals_["_verify_payout_receipts"]
    globals_["_verify_payout_receipts"] = lambda *args: {"outcome": "UNAVAILABLE"}
    try:
        with direct_vm.expect_revert("retry reconciliation"):
            hub.reconcile_withdrawal(withdrawal_id, parent_tx, child_tx)
        assert hub.get_withdrawal(withdrawal_id)["status"] == "PENDING"
        assert hub.get_pending_outbound(recipient) == "500"
        assert receipt_key not in hub.consumed_payout_receipts
    finally:
        globals_["_verify_payout_receipts"] = original


def test_withdraw_blocks_a_second_pending_withdrawal_for_the_same_recipient(direct_vm, direct_deploy):
    """withdraw() itself (not just reconciliation) must serialize per recipient."""
    recipient = _address("4")
    hub = direct_deploy(HUB, "", "", True)
    address = hub._instance.withdraw.__globals__["Address"](recipient)
    hub.credits[address] = 1000
    hub.claimable = 1000
    direct_vm.deal(direct_vm._contract_address, 1000)
    direct_vm.sender = bytes.fromhex(recipient[2:])

    hub.withdraw()
    assert hub.get_credit(recipient) == "0"
    assert hub.get_pending_outbound(recipient) == "1000"
    first_withdrawal = hub.get_latest_withdrawal(recipient)
    assert first_withdrawal["status"] == "PENDING"

    # A second credit arrives while the first withdrawal is still unreconciled.
    hub.credits[address] = 500
    hub.claimable = 500
    with direct_vm.expect_revert("reconcile the existing withdrawal before starting another"):
        hub.withdraw()
    assert hub.get_credit(recipient) == "500"
    assert hub.get_pending_outbound(recipient) == "1000"


def test_withdraw_refuses_to_send_when_hub_is_underfunded(direct_vm, direct_deploy):
    """The solvency guard must trip before any external value message is emitted."""
    recipient = _address("4")
    hub = direct_deploy(HUB, "", "", True)
    address = hub._instance.withdraw.__globals__["Address"](recipient)
    hub.credits[address] = 1000
    hub.claimable = 1000
    direct_vm.deal(direct_vm._contract_address, 500)
    direct_vm.sender = bytes.fromhex(recipient[2:])

    with direct_vm.expect_revert("Hub is underfunded; recapitalize before withdrawing"):
        hub.withdraw()
    assert hub.get_credit(recipient) == "1000"
    assert hub.get_pending_outbound(recipient) == "0"


def test_out_of_order_attestation_callback_violates_fifo_and_reverts(direct_vm, direct_deploy):
    """record_attestation must reject a callback for anything but the queue head."""
    witness, researcher_a, researcher_b = _address("9"), _address("2"), _address("3")
    hub = direct_deploy(HUB, "", "", True)
    hub.witness_address = witness
    hub.configured = True
    dossier = {"id": "noema-stateful", "sponsor": _address("1"), "status": "OPEN",
        "reward_atto": "1000", "rules_root": "a" * 64, "manifest_root": "b" * 64,
        "evidence": [], "active_ids": ["note-1", "note-2"], "queue": ["note-1", "note-2"],
        "pending_id": "note-2", "stage_deadline": "100", "next_queue_position": 3,
        "submission_ids": ["note-1", "note-2"], "closes_at": "99999999999"}
    sub1 = {"id": "note-1", "dossier_id": "noema-stateful", "researcher": researcher_a,
            "status": "QUEUED", "bond_atto": "100", "bond_released": False}
    # note-2 is impossibly already WITNESS_PENDING/pending_id while note-1 still heads the
    # queue: only reachable by forging state, which is exactly what this guard defends against.
    sub2 = {"id": "note-2", "dossier_id": "noema-stateful", "researcher": researcher_b,
            "status": "WITNESS_PENDING", "bond_atto": "100", "bond_released": False}
    hub.dossiers[dossier["id"]] = json.dumps(dossier)
    hub.submissions["note-1"] = json.dumps(sub1)
    hub.submissions["note-2"] = json.dumps(sub2)

    direct_vm.sender = bytes.fromhex(witness[2:])
    with direct_vm.expect_revert("FIFO attestation order violation"):
        hub.record_attestation("note-2", json.dumps({"status": "ATTESTED"}))
    # Neither submission's bond moved and the queue order is untouched.
    assert hub.get_submission("note-2")["status"] == "WITNESS_PENDING"
    assert hub.get_dossier("noema-stateful")["queue"] == ["note-1", "note-2"]


def test_out_of_order_verdict_callback_violates_fifo_and_reverts(direct_vm, direct_deploy):
    """record_verdict must reject a callback for anything but the queue head."""
    engine, researcher_a, researcher_b = _address("9"), _address("2"), _address("3")
    hub = direct_deploy(HUB, "", "", True)
    hub.engine_address = engine
    hub.configured = True
    hub.reward_escrow = 1000
    dossier = {"id": "noema-stateful", "sponsor": _address("1"), "status": "OPEN",
        "reward_atto": "1000", "rules_root": "a" * 64, "manifest_root": "b" * 64,
        "evidence": [_evidence("note-1"), _evidence("note-2")],
        "active_ids": ["note-1", "note-2"], "queue": ["note-1", "note-2"],
        "pending_id": "note-2", "stage_deadline": "100", "next_queue_position": 3,
        "submission_ids": ["note-1", "note-2"], "closes_at": "99999999999"}
    sub1 = {"id": "note-1", "dossier_id": "noema-stateful", "researcher": researcher_a,
            "status": "QUEUED", "bond_atto": "100", "bond_released": False}
    sub2 = {"id": "note-2", "dossier_id": "noema-stateful", "researcher": researcher_b,
            "status": "VERDICT_PENDING", "bond_atto": "100", "bond_released": False}
    hub.dossiers[dossier["id"]] = json.dumps(dossier)
    hub.submissions["note-1"] = json.dumps(sub1)
    hub.submissions["note-2"] = json.dumps(sub2)

    direct_vm.sender = bytes.fromhex(engine[2:])
    result = {"outcome": "POSITION_A", "sufficient": True, "decisive_ids": ["note-2"],
        "basis": "decisive", "basis_digest": "c" * 64, "rules_root": dossier["rules_root"],
        "manifest_root": dossier["manifest_root"], "counterfactual_outcome": "UNRESOLVED",
        "contribution_required": True}
    with direct_vm.expect_revert("FIFO verdict order violation"):
        hub.record_verdict("note-2", json.dumps(result))
    # The reward must still be fully in escrow: no reward can be paid out of order.
    assert int(hub.reward_escrow) == 1000
    assert hub.get_submission("note-2")["status"] == "VERDICT_PENDING"


def test_accounting_invariant_holds_through_a_full_loss_and_recapitalization(direct_vm, direct_deploy):
    """Demonstrate the economically consequential consensus end to end: a real backing
    loss on a failed payout must make accounting_ok false, and recapitalize_payouts
    must be able to restore it -- the invariant is load-bearing, not cosmetic."""
    recipient = _address("4")
    parent_tx, child_tx = "0x" + "1" * 64, "0x" + "2" * 64
    hub = direct_deploy(HUB, "", "", True)
    address = hub._instance.withdraw.__globals__["Address"](recipient)
    hub.deposited = 1000
    hub.claimable = 1000
    hub.credits[address] = 1000
    direct_vm.deal(direct_vm._contract_address, 1000)
    direct_vm.sender = bytes.fromhex(recipient[2:])

    assert hub.get_stats()["accounting_ok"] is True
    hub.withdraw()
    assert hub.get_stats()["accounting_ok"] is True

    withdrawal_id = hub.get_latest_withdrawal(recipient)["id"]
    item = hub.get_withdrawal(withdrawal_id)
    # The GEN genuinely left the Hub's custody and was not returned: a real loss.
    direct_vm.deal(direct_vm._contract_address, 0)
    globals_ = hub._instance.reconcile_withdrawal.__globals__
    original = globals_["_verify_payout_receipts"]
    globals_["_verify_payout_receipts"] = lambda *args: {
        "outcome": "FAILED", "parent_id": parent_tx, "child_id": child_tx,
        "recipient": recipient, "amount": item["amount"], "withdrawal_created_at": item["created_at"]}
    try:
        hub.reconcile_withdrawal(withdrawal_id, parent_tx, child_tx)
    finally:
        globals_["_verify_payout_receipts"] = original

    stats = hub.get_stats()
    assert int(hub.payout_loss) == 1000
    assert stats["accounting_ok"] is False
    assert stats["payout_recovery_required"] == "1000"

    # recapitalize_payouts is payable: the GEN actually arrives in the Hub's balance.
    direct_vm.value = 1000
    direct_vm.deal(direct_vm._contract_address, 1000)
    hub.recapitalize_payouts()
    direct_vm.value = 0

    stats = hub.get_stats()
    assert stats["accounting_ok"] is True
    assert stats["payout_recovery_required"] == "0"
    assert int(hub.deposited) == 2000
