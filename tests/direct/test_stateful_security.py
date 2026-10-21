import hashlib
import json
import re


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
        "question": "Does the fixture question hold?",
        "decision_rule": "Resolve A when the fixture evidence establishes it.",
        "position_a": "A", "position_b": "B", "source_policy": "Accept any fixture source.",
        "evidence": [{"id": "note-1"}],
        "active_ids": ["note-1"],
        "queue": ["note-1"],
        "pending_id": "note-1",
        "stage_deadline": "99999999999",
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
        "pending_id": "note-2", "stage_deadline": "99999999999", "next_queue_position": 3,
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
        "pending_id": "note-2", "stage_deadline": "99999999999", "next_queue_position": 3,
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


def test_late_attestation_callback_after_deadline_reverts_then_expire_stage_succeeds(
    direct_vm, direct_deploy
):
    """A worker callback and expire_stage() must never both be able to act on the
    same stage: once the deadline has elapsed, only the timeout path may finalize it."""
    witness, researcher = _address("9"), _address("2")
    hub = direct_deploy(HUB, "", "", True)
    hub.witness_address = witness
    hub.configured = True
    dossier = _base_dossier(_address("1"), researcher)
    dossier["stage_deadline"] = "100"
    dossier["closes_at"] = "99999999999"
    submission = {**_submission(researcher), "status": "WITNESS_PENDING"}
    hub.dossiers[dossier["id"]] = json.dumps(dossier)
    hub.submissions[submission["id"]] = json.dumps(submission)
    hub.bond_escrow = 100

    direct_vm.warp("1970-01-01T00:01:41Z")  # 101s: at/after the stage deadline
    direct_vm.sender = bytes.fromhex(witness[2:])
    with direct_vm.expect_revert("semantic stage deadline elapsed; call expire_stage"):
        hub.record_attestation("note-1", json.dumps({"status": "ATTESTED"}))
    assert hub.get_submission("note-1")["status"] == "WITNESS_PENDING"

    # Only the timeout path may act now, and it does.
    hub.expire_stage(dossier["id"])
    assert hub.get_submission("note-1")["status"] == "INCONCLUSIVE_TIMEOUT"
    assert hub.get_credit(researcher) == "100"


def test_late_verdict_callback_after_deadline_reverts_then_expire_stage_rolls_back(
    direct_vm, direct_deploy
):
    """The same exclusivity must hold for record_verdict: a late decisive verdict
    can never race an expiry rollback for the same bond and reward."""
    engine, researcher = _address("9"), _address("2")
    hub = direct_deploy(HUB, "", "", True)
    hub.engine_address = engine
    hub.configured = True
    hub.reward_escrow = 1000
    dossier = _base_dossier(_address("1"), researcher)
    dossier["stage_deadline"] = "100"
    dossier["evidence"] = [_evidence("note-1")]
    submission = _submission(researcher, "VERDICT_PENDING")
    hub.dossiers[dossier["id"]] = json.dumps(dossier)
    hub.submissions[submission["id"]] = json.dumps(submission)
    hub.bond_escrow = 100

    direct_vm.warp("1970-01-01T00:01:41Z")
    direct_vm.sender = bytes.fromhex(engine[2:])
    result = {"outcome": "POSITION_A", "decisive_ids": ["note-1"], "rules_root": dossier["rules_root"],
              "manifest_root": dossier["manifest_root"], "counterfactual_outcome": "UNRESOLVED",
              "contribution_required": True}
    with direct_vm.expect_revert("semantic stage deadline elapsed; call expire_stage"):
        hub.record_verdict("note-1", json.dumps(result))
    # No reward can have moved: the late verdict never took effect.
    assert int(hub.reward_escrow) == 1000
    assert hub.get_submission("note-1")["status"] == "VERDICT_PENDING"

    hub.expire_stage(dossier["id"])
    assert hub.get_submission("note-1")["status"] == "INCONCLUSIVE_TIMEOUT"
    assert hub.get_credit(researcher) == "100"
    assert int(hub.reward_escrow) == 1000
    # The tentatively appended candidate evidence was rolled back.
    assert hub.get_dossier(dossier["id"])["evidence"] == []


def test_expire_dossier_defers_while_adjudication_is_still_within_its_own_deadline(
    direct_vm, direct_deploy
):
    """closes_at (research admission) and stage_deadline (in-flight adjudication) are
    distinct: a sponsor cannot be refunded out from under a submission that is still
    legitimately being witnessed or resolved."""
    sponsor, researcher = _address("1"), _address("2")
    hub = direct_deploy(HUB, "", "", True)
    dossier = _base_dossier(sponsor, researcher)
    dossier["closes_at"] = "50"
    dossier["stage_deadline"] = "99999999999"
    hub.dossiers[dossier["id"]] = json.dumps(dossier)
    hub.submissions["note-1"] = json.dumps({**_submission(researcher), "status": "WITNESS_PENDING"})
    hub.reward_escrow = 1000
    hub.bond_escrow = 100

    direct_vm.warp("1970-01-01T00:16:40Z")  # 1000s: past closes_at, far before stage_deadline
    with direct_vm.expect_revert("in-flight adjudication must resolve or expire before dossier closure"):
        hub.expire_dossier(dossier["id"])
    # The sponsor's reward was not touched by the blocked attempt.
    assert hub.get_dossier(dossier["id"])["status"] == "OPEN"
    assert int(hub.reward_escrow) == 1000

    # Once the adjudication's own deadline has also elapsed, closure is allowed.
    dossier["stage_deadline"] = "500"
    hub.dossiers[dossier["id"]] = json.dumps(dossier)
    hub.expire_dossier(dossier["id"])
    assert hub.get_dossier(dossier["id"])["status"] == "CLOSED_REFUNDED"
    assert int(hub.reward_escrow) == 0
    assert hub.get_credit(sponsor) == "1000"


def test_unavailable_callback_forfeits_bond_to_sponsor_not_researcher(direct_vm, direct_deploy):
    """The researcher's own chosen source returning a temporary status is
    fully within their control; it may not be a free way to burn through
    the dossier's bounded lifetime capacity."""
    witness, sponsor, researcher = _address("9"), _address("1"), _address("2")
    hub = direct_deploy(HUB, "", "", True)
    hub.witness_address = witness
    hub.configured = True
    direct_vm.sender = bytes.fromhex(witness[2:])

    dossier = _base_dossier(sponsor, researcher)
    dossier["closes_at"] = "99999999999"
    hub.dossiers[dossier["id"]] = json.dumps(dossier)
    hub.submissions["note-1"] = json.dumps({**_submission(researcher), "status": "WITNESS_PENDING",
                                            "url": "https://example.test/a", "claim": "x"})
    hub.bond_escrow = 100
    hub.record_attestation("note-1", json.dumps({"status": "UNAVAILABLE"}))
    assert hub.get_submission("note-1")["status"] == "RETRYABLE"
    assert hub.get_credit(sponsor) == "100"
    assert hub.get_credit(researcher) == "0"
    assert int(hub.bond_escrow) == 0


def _attested_result(hub, url, claim):
    sha = hub._instance.record_attestation.__globals__["_sha"]
    return {"status": "ATTESTED", "claim_digest": sha(claim.strip()), "requested_url": url,
            "provenance_status": "VERIFIED_DIRECT_RESPONSE", "transport_origin_verified": True,
            "verified_response_origin": "https://example.test", "content_digest": "a" * 64,
            "support_digest": "b" * 64, "support_quote": "verbatim support", "requested_origin": "https://example.test",
            "requested_host": "example.test", "claim": claim, "observed_at": "2026-10-21T00:00:00+00:00",
            "http_status": 200, "source_size": 128}


def test_queued_submission_witnessed_after_closes_at_is_not_penalized_for_queue_delay(
    direct_vm, direct_deploy
):
    """seal_disclosure guarantees every disclosed submission was revealed
    strictly before closes_at. Witnessing it late is FIFO queue delay, never
    the researcher's choice, so it must proceed on its merits -- never be
    forfeited just because closes_at has numerically elapsed by the time the
    witness responds."""
    witness, engine, sponsor, researcher = _address("9"), _address("8"), _address("1"), _address("2")
    hub = direct_deploy(HUB, "", "", True)
    hub.witness_address = witness
    hub.engine_address = engine
    hub.configured = True
    direct_vm.sender = bytes.fromhex(witness[2:])

    dossier = _base_dossier(sponsor, researcher)
    dossier["closes_at"] = "50"  # already elapsed: pure queue-delay scenario
    dossier["stage_deadline"] = "99999999999"
    dossier["evidence"] = []  # attestation below appends its own real record for note-1
    hub.dossiers[dossier["id"]] = json.dumps(dossier)
    hub.submissions["note-1"] = json.dumps({**_submission(researcher), "status": "WITNESS_PENDING",
                                            "url": "https://example.test/a", "claim": "the disclosed fact"})
    hub.bond_escrow = 100
    direct_vm.warp("1970-01-01T00:16:40Z")  # 1000s: long past closes_at, well before stage_deadline

    hub.record_attestation("note-1", json.dumps(_attested_result(hub, "https://example.test/a", "the disclosed fact")))

    submission = hub.get_submission("note-1")
    assert submission["status"] == "VERDICT_PENDING"
    # The bond is still locked pending an actual outcome -- not forfeited,
    # not refunded early, exactly as if closes_at had never been reached.
    assert int(hub.bond_escrow) == 100
    assert hub.get_credit(sponsor) == "0"
    assert hub.get_credit(researcher) == "0"
    assert [item["id"] for item in hub.get_dossier(dossier["id"])["evidence"]] == ["note-1"]


def test_decisive_settlement_still_pays_full_reward_after_closes_at_from_queue_delay(
    direct_vm, direct_deploy
):
    """A submission that was timely disclosed and is actually decisive must be
    paid in full, even though the queue only reached its verdict after
    closes_at -- the reward depends on the evidence, never on queue timing."""
    sponsor, researcher, engine = _address("1"), _address("2"), _address("3")
    hub = direct_deploy(HUB, "", "", True)
    hub.engine_address = engine
    hub.configured = True
    hub.reward_escrow = 1000
    hub.bond_escrow = 100
    dossier = _base_dossier(sponsor, researcher)
    dossier["closes_at"] = "50"  # already elapsed by the time the verdict lands
    dossier["stage_deadline"] = "99999999999"
    dossier["evidence"] = [_evidence("note-1")]
    submission = _submission(researcher, "VERDICT_PENDING")
    hub.dossiers[dossier["id"]] = json.dumps(dossier)
    hub.submissions[submission["id"]] = json.dumps(submission)

    direct_vm.warp("1970-01-01T00:16:40Z")  # 1000s: past closes_at
    direct_vm.sender = bytes.fromhex(engine[2:])
    result = {"outcome": "POSITION_A", "decisive_ids": ["note-1"], "rules_root": dossier["rules_root"],
              "manifest_root": dossier["manifest_root"], "counterfactual_outcome": "UNRESOLVED",
              "contribution_required": True, "basis": "decisive despite queue delay"}
    hub.record_verdict("note-1", json.dumps(result))

    final_dossier = hub.get_dossier(dossier["id"])
    final_submission = hub.get_submission("note-1")
    assert final_dossier["status"] == "RESOLVED"
    assert final_dossier["winner"] == researcher
    assert final_submission["status"] == "DECISIVE"
    # Full reward plus the returned bond, exactly as if closure had not yet happened.
    assert hub.get_credit(researcher) == "1100"
    assert int(hub.reward_escrow) == 0
    assert int(hub.bond_escrow) == 0


def test_genuine_stage_timeout_after_closes_at_still_refunds_researcher_not_sponsor(
    direct_vm, direct_deploy
):
    """Distinguish the two kinds of 'late': closes_at alone never penalizes a
    queued submission, but a genuine stage timeout (the worker itself never
    responded within its own deadline) is a different, already-fair outcome
    that refunds the researcher -- and the two must never compete for the
    same submission. A callback arriving after the stage deadline is
    rejected regardless of closes_at; only expire_stage may act."""
    witness, sponsor, researcher = _address("9"), _address("1"), _address("2")
    hub = direct_deploy(HUB, "", "", True)
    hub.witness_address = witness
    hub.configured = True
    dossier = _base_dossier(sponsor, researcher)
    dossier["closes_at"] = "50"
    dossier["stage_deadline"] = "100"  # both deadlines elapsed together
    hub.dossiers[dossier["id"]] = json.dumps(dossier)
    hub.submissions["note-1"] = json.dumps({**_submission(researcher), "status": "WITNESS_PENDING"})
    hub.bond_escrow = 100

    direct_vm.warp("1970-01-01T00:01:41Z")  # 101s: past both closes_at and stage_deadline
    direct_vm.sender = bytes.fromhex(witness[2:])
    with direct_vm.expect_revert("semantic stage deadline elapsed; call expire_stage"):
        hub.record_attestation("note-1", json.dumps(_attested_result(hub, "https://example.test/a", "x")))
    assert hub.get_submission("note-1")["status"] == "WITNESS_PENDING"

    hub.expire_stage(dossier["id"])
    assert hub.get_submission("note-1")["status"] == "INCONCLUSIVE_TIMEOUT"
    assert hub.get_credit(researcher) == "100"
    assert hub.get_credit(sponsor) == "0"


def test_fifo_queue_of_submissions_disclosed_before_closure_drains_fairly(direct_vm, direct_deploy):
    """Two submissions disclosed before closes_at but still queued when it
    elapses: the head is witnessed and settled on its merits, and the queue
    then correctly advances to the next submission, all without either
    being penalized for closure timing."""
    witness, engine, sponsor, researcher_a, researcher_b = _address("9"), _address("8"), _address("1"), _address("2"), _address("3")
    hub = direct_deploy(HUB, "", "", True)
    hub.witness_address = witness
    hub.engine_address = engine
    hub.configured = True
    dossier = _base_dossier(sponsor, researcher_a)
    dossier["closes_at"] = "50"
    dossier["stage_deadline"] = "99999999999"
    dossier["active_ids"] = ["note-1", "note-2"]
    dossier["queue"] = ["note-1", "note-2"]
    dossier["submission_ids"] = ["note-1", "note-2"]
    dossier["evidence"] = []  # attestation below appends its own real record for note-1
    hub.dossiers[dossier["id"]] = json.dumps(dossier)
    hub.submissions["note-1"] = json.dumps({**_submission(researcher_a), "status": "WITNESS_PENDING",
                                            "url": "https://example.test/a", "claim": "claim a"})
    hub.submissions["note-2"] = json.dumps({"id": "note-2", "dossier_id": dossier["id"],
        "researcher": researcher_b, "status": "QUEUED", "bond_atto": "100", "bond_released": False,
        "url": "https://example.test/b", "claim": "claim b"})
    hub.bond_escrow = 200

    direct_vm.warp("1970-01-01T00:16:40Z")  # 1000s: past closes_at, queue still draining
    direct_vm.sender = bytes.fromhex(witness[2:])
    hub.record_attestation("note-1", json.dumps(_attested_result(hub, "https://example.test/a", "claim a")))
    assert hub.get_submission("note-1")["status"] == "VERDICT_PENDING"

    # A non-decisive verdict refunds note-1 and must advance the queue to note-2.
    engine_result = {"outcome": "UNRESOLVED", "sufficient": False, "decisive_ids": [],
        "basis": "non-decisive", "basis_digest": "c" * 64, "rules_root": dossier["rules_root"],
        "manifest_root": hub.get_dossier(dossier["id"])["manifest_root"],
        "counterfactual_outcome": "", "contribution_required": False}
    direct_vm.sender = bytes.fromhex(engine[2:])
    hub.record_verdict("note-1", json.dumps(engine_result))

    assert hub.get_submission("note-1")["status"] == "ATTESTED_NON_DECISIVE"
    assert hub.get_credit(researcher_a) == "100"
    final_dossier = hub.get_dossier(dossier["id"])
    assert final_dossier["status"] == "OPEN"
    assert final_dossier["queue"] == ["note-2"]
    assert hub.get_submission("note-2")["status"] == "WITNESS_PENDING"
    assert final_dossier["pending_id"] == "note-2"


def test_attestation_valid_treats_content_addressed_and_direct_response_as_distinct(
    direct_deploy,
):
    """transport_origin_verified must never be conflated with content-addressed
    assurance: each provenance_status is accepted only with its own matching
    transport_origin_verified value, never the other's."""
    hub = direct_deploy(HUB, "", "", True)
    valid = {"status": "ATTESTED", "claim_digest": "", "requested_url": "https://example.test/a",
             "verified_response_origin": "https://example.test", "content_digest": "a" * 64,
             "support_digest": "b" * 64, "support_quote": "quote"}

    def check(**overrides):
        result = {**valid, **overrides}
        result["claim_digest"] = hub._instance._attestation_valid.__globals__["_sha"]("claim")
        return hub._instance._attestation_valid(result, "https://example.test/a", "claim")

    assert check(provenance_status="VERIFIED_DIRECT_RESPONSE", transport_origin_verified=True) is True
    assert check(provenance_status="VERIFIED_CONTENT_ADDRESSED_ORIGIN", transport_origin_verified=False) is True
    # Neither may borrow the other's transport_origin_verified value.
    assert check(provenance_status="VERIFIED_DIRECT_RESPONSE", transport_origin_verified=False) is False
    assert check(provenance_status="VERIFIED_CONTENT_ADDRESSED_ORIGIN", transport_origin_verified=True) is False
    assert check(provenance_status="UNVERIFIED_RESPONSE_ORIGIN", transport_origin_verified=True) is False


def test_misleading_attested_claim_with_quote_absent_from_body_is_rejected(direct_vm, direct_deploy):
    """Authenticated source bytes are not the same thing as an independently
    verified claim: a document that was legitimately and correctly fetched
    and hashed does not by itself establish anything. If the model claims
    ATTESTED but its support_quote is not actually present verbatim in the
    fetched bytes, the contract must force REJECTED regardless of whatever
    booleans or basis prose the model returned."""
    # GenVM's current web response never exposes a final URL (its Response
    # type carries only status/headers/body), so admissible provenance
    # requires the immutable content-addressed GitHub allowlist even in
    # this harness -- exactly as on the real network.
    hub = _address("9")
    url = "https://raw.githubusercontent.com/test-org/test-repo/" + "a" * 40 + "/FILE"
    witness = direct_deploy(WITNESS, hub)
    direct_vm.sender = bytes.fromhex(hub[2:])
    body = "The document discusses an unrelated matter and never states the claimed fact."
    direct_vm.mock_web(re.escape(url), {"status": 200, "body": body})
    direct_vm.mock_llm("NOEMA_SOURCE_WITNESS_V1", json.dumps({
        "same_subject": True, "policy_compliant": True, "claim_supported": True,
        "time_aligned": True, "materially_new": True, "internally_consistent": True,
        "support_quote": "This exact sentence never appears in the fetched document.",
        "basis": "The model incorrectly claims the document supports the fact."}))

    witness.attest("req-1", hub, "question", "rule", "policy", "[]", url, "the claimed fact")

    record = witness.get_record("req-1")
    assert record["status"] == "REJECTED"
    for field in ("same_subject", "policy_compliant", "claim_supported", "time_aligned",
                  "materially_new", "internally_consistent"):
        assert record[field] is False
    assert record["support_quote"] == ""
    assert record["support_digest"] == ""
    # The byte-level facts are still recorded and correct, even though the
    # semantic claim they were paired with was rejected.
    assert record["content_digest"] == hashlib.sha256(body.encode()).hexdigest()
    assert record["http_status"] == 200


def test_attested_claim_with_quote_present_in_body_is_accepted(direct_vm, direct_deploy):
    """Positive control for the above: when the quoted passage genuinely is
    present verbatim, the same pipeline accepts it."""
    hub = _address("9")
    url = "https://raw.githubusercontent.com/test-org/test-repo/" + "b" * 40 + "/FILE"
    witness = direct_deploy(WITNESS, hub)
    direct_vm.sender = bytes.fromhex(hub[2:])
    body = "Preamble. The exact fact in question is clearly true. Trailer."
    direct_vm.mock_web(re.escape(url), {"status": 200, "body": body})
    direct_vm.mock_llm("NOEMA_SOURCE_WITNESS_V1", json.dumps({
        "same_subject": True, "policy_compliant": True, "claim_supported": True,
        "time_aligned": True, "materially_new": True, "internally_consistent": True,
        "support_quote": "The exact fact in question is clearly true.",
        "basis": "The document states the fact verbatim."}))

    witness.attest("req-2", hub, "question", "rule", "policy", "[]", url, "the exact fact")

    record = witness.get_record("req-2")
    assert record["status"] == "ATTESTED"
    assert record["support_quote"] == "The exact fact in question is clearly true."
    assert record["support_digest"] == hashlib.sha256(record["support_quote"].encode()).hexdigest()
