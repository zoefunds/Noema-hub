import hashlib
import json


HUB = "contracts/noema_hub.py"
ENGINE = "contracts/verdict_engine.py"


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
        "claim_digest": "1" * 64,
        "content_digest": "2" * 64,
        "support_digest": "3" * 64,
        "verified_response_origin": "https://example.test",
    }


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
        "outcome": "UNRESOLVED", "decisive_ids": []
    }))
    result = decide(
        "What is the beacon state?",
        "Resolve only when two authenticated sources agree; conflicts are unresolved.",
        "RED", "BLUE", "a" * 64, json.dumps(manifest), "evidence-blue"
    )
    assert result["outcome"] == "UNRESOLVED"
    assert result["decisive_ids"] == []
    assert result["contribution_required"] is False
    # The validator re-executes the same source-bound prompt and must agree.
    assert direct_vm.run_validator(index=-2) is True
    assert direct_vm.run_validator(index=-1) is True


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
