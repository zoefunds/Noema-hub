# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import hashlib
import json
import re
from datetime import datetime, timezone

VERSION = "1.0.0"
CHAIN_ID = "61999"
MIN_REWARD = 10 ** 15
MAX_REWARD = 10 * 10 ** 18
MIN_BOND = 10 ** 14
MAX_BASELINE = 4
MAX_ACTIVE = 24
MAX_EVIDENCE = 18
MAX_LIFETIME_SUBMISSIONS = 72
MAX_DECISIVE_IDS = 12
MAX_PAGE = 24
REVEAL_WINDOW = 1200
STAGE_WINDOW = 1800
STUDIONET_RPC = "https://studio.genlayer.com/api"
WITHDRAW_CALLDATA = "DgZtZXRob2REd2l0aGRyYXc="


@gl.evm.contract_interface
class _EvmRecipient:
    class View:
        pass
    class Write:
        pass


def _now():
    return int(datetime.fromisoformat(gl.message_raw["datetime"]).timestamp())


def _iso():
    return datetime.fromtimestamp(_now(), tz=timezone.utc).isoformat()


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _text(value, name, maximum, minimum=1):
    if not isinstance(value, str) or "\x00" in value or not minimum <= len(value.strip()) <= maximum:
        raise gl.vm.UserError(f"[EXPECTED] invalid {name}")
    return value.strip()


def _address(value, name):
    value = str(value).replace("addr#", "0x").replace("address#", "0x")
    if re.fullmatch(r"0x[0-9a-fA-F]{40}", value) is None or int(value[2:], 16) == 0:
        raise gl.vm.UserError(f"[EXPECTED] invalid {name} address")
    return value


def _commitment(hub, dossier_id, researcher, url, claim, salt):
    return _sha(_json({"domain": "NOEMA_DISCLOSURE_V1", "chain_id": CHAIN_ID,
        "hub": hub.lower(), "dossier_id": dossier_id, "researcher": researcher.lower(),
        "url": url, "claim": claim, "salt": salt}))


def _manifest_root(items):
    return _sha(_json([{"id": i["id"], "claim_digest": i["claim_digest"],
                        "content_digest": i["content_digest"], "source_host": i["source_host"]}
                       for i in items]))


def _tx_id(transaction):
    return str(transaction.get("tx_id", transaction.get("id", ""))).lower()


def _tx_value(value):
    try:
        return int(value, 0) if isinstance(value, str) else int(value)
    except Exception:
        return -1


def _tx_address(value):
    return str(value).replace("addr#", "0x").replace("address#", "0x").lower()


def _tx_timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except Exception:
        return -1


def _realized_payout_loss(amount, liabilities_before, assets_before, liabilities_after, assets_after):
    deficit_before = max(0, liabilities_before - assets_before)
    uncovered_after = max(0, liabilities_after - assets_after)
    return min(amount, max(0, uncovered_after - deficit_before))


def _payout_receipt_outcome(parent, child, parent_id, child_id, hub, recipient, amount, withdrawal_created_at):
    """Validate a finalized Hub withdrawal and its exact external child record."""
    if not isinstance(parent, dict) or not isinstance(child, dict):
        return "INVALID"
    if _tx_id(parent) != parent_id.lower() or _tx_id(child) != child_id.lower():
        return "INVALID"
    if str(parent.get("status", "")).upper() != "FINALIZED" or str(child.get("status", "")).upper() != "FINALIZED":
        return "PENDING"
    if _tx_address(parent.get("from_address", parent.get("sender", ""))) != recipient.lower():
        return "INVALID"
    if _tx_address(parent.get("to_address", parent.get("recipient", ""))) != hub.lower():
        return "INVALID"
    if _tx_timestamp(parent.get("created_at")) != _tx_timestamp(withdrawal_created_at):
        return "INVALID"
    calldata = parent.get("data", {}).get("calldata", "") if isinstance(parent.get("data"), dict) else ""
    if calldata != WITHDRAW_CALLDATA:
        return "INVALID"
    # The StudioNet `eth_getTransactionByHash` response keeps
    # `triggered_transactions` empty for external EVM messages. Linkage is
    # instead established by the child's `triggered_by` plus this exact parent
    # message; do not treat the empty convenience field as proof of absence.
    messages = parent.get("messages", [])
    if not isinstance(messages, list):
        return "INVALID"
    matching_messages = [message for message in messages if isinstance(message, dict)
        and _tx_address(message.get("recipient", "")) == recipient.lower()
        and _tx_value(message.get("value")) == amount
        and message.get("onAcceptance") is False]
    if len(matching_messages) != 1:
        return "INVALID"
    if str(child.get("triggered_by", child.get("triggered_by_hash", ""))).lower() != parent_id.lower():
        return "INVALID"
    if _tx_address(child.get("from_address", child.get("sender", ""))) != hub.lower():
        return "INVALID"
    if _tx_address(child.get("to_address", child.get("recipient", ""))) != recipient.lower():
        return "INVALID"
    if _tx_value(child.get("value")) != amount or type(child.get("value_credited")) is not bool:
        return "INVALID"
    return "DELIVERED" if child["value_credited"] else "FAILED"


def _fetch_studionet_transaction(txid):
    response = gl.nondet.web.request(STUDIONET_RPC, method="POST", body={
        "jsonrpc": "2.0", "id": 1, "method": "eth_getTransactionByHash", "params": [txid]})
    status = int(getattr(response, "status_code", getattr(response, "status", 0)))
    if status != 200:
        raise ValueError("StudioNet transaction lookup failed")
    body = response.body.decode("utf-8") if isinstance(response.body, bytes) else str(response.body)
    payload = json.loads(body)
    if payload.get("error") or not isinstance(payload.get("result"), dict):
        raise ValueError("StudioNet transaction receipt is unavailable")
    return payload["result"]


def _verify_payout_receipts(parent_id, child_id, hub, recipient, amount, withdrawal_created_at):
    def leader_fn():
        try:
            parent = _fetch_studionet_transaction(parent_id)
            child = _fetch_studionet_transaction(child_id)
            outcome = _payout_receipt_outcome(parent, child, parent_id, child_id, hub, recipient, amount,
                                              withdrawal_created_at)
            return {"outcome": outcome, "parent_id": parent_id.lower(), "child_id": child_id.lower(),
                    "recipient": recipient.lower(), "amount": str(amount),
                    "withdrawal_created_at": withdrawal_created_at}
        except Exception:
            return {"outcome": "UNAVAILABLE", "parent_id": parent_id.lower(), "child_id": child_id.lower(),
                    "recipient": recipient.lower(), "amount": str(amount),
                    "withdrawal_created_at": withdrawal_created_at}

    def validator_fn(leader_result):
        if not isinstance(leader_result, gl.vm.Return):
            return False
        try:
            return leader_fn() == leader_result.calldata
        except Exception:
            return False

    return gl.vm.run_nondet_unsafe(leader_fn, validator_fn)


class NoemaHub(gl.Contract):
    dossiers: TreeMap[str, str]
    dossier_ids: DynArray[str]
    submissions: TreeMap[str, str]
    commitments: TreeMap[str, str]
    reservations: TreeMap[str, str]
    credits: TreeMap[Address, u256]
    pending_outbound: TreeMap[Address, u256]
    latest_withdrawal_id: TreeMap[Address, str]
    withdrawal_nonce: TreeMap[Address, u256]
    withdrawals: TreeMap[str, str]
    native_payouts_enabled: bool
    witness_address: str
    engine_address: str
    bootstrapper: str
    configured: bool
    next_dossier: u256
    next_submission: u256
    deposited: u256
    reward_escrow: u256
    bond_escrow: u256
    claimable: u256
    withdrawn: u256
    pending_outbound_total: u256
    payout_loss: u256
    recovery_surplus: u256

    def __init__(self, witness_address: str, engine_address: str, native_payouts_enabled: bool):
        self.bootstrapper = str(gl.message.sender_address)
        self.configured = bool(witness_address and engine_address)
        self.witness_address = _address(witness_address, "witness") if witness_address else ""
        self.engine_address = _address(engine_address, "engine") if engine_address else ""
        self.native_payouts_enabled = native_payouts_enabled
        self.next_dossier = u256(1)
        self.next_submission = u256(1)
        self.deposited = u256(0)
        self.reward_escrow = u256(0)
        self.bond_escrow = u256(0)
        self.claimable = u256(0)
        self.withdrawn = u256(0)
        self.pending_outbound_total = u256(0)
        self.payout_loss = u256(0)
        self.recovery_surplus = u256(0)

    @gl.public.write
    def configure(self, witness_address: str, engine_address: str) -> None:
        if self.configured or str(gl.message.sender_address).lower() != self.bootstrapper.lower():
            raise gl.vm.UserError("[EXPECTED] one-time bootstrap only")
        self.witness_address = _address(witness_address, "witness")
        self.engine_address = _address(engine_address, "engine")
        self.configured = True
        self.bootstrapper = ""

    def _dossier(self, dossier_id):
        if dossier_id not in self.dossiers:
            raise gl.vm.UserError("[EXPECTED] dossier not found")
        return json.loads(self.dossiers[dossier_id])

    def _submission(self, submission_id):
        if submission_id not in self.submissions:
            raise gl.vm.UserError("[EXPECTED] submission not found")
        return json.loads(self.submissions[submission_id])

    def _save_dossier(self, value):
        self.dossiers[value["id"]] = _json(value)

    def _save_submission(self, value):
        self.submissions[value["id"]] = _json(value)

    def _credit(self, address, amount):
        target = Address(address)
        current = int(self.credits[target]) if target in self.credits else 0
        self.credits[target] = u256(current + amount)
        self.claimable = u256(int(self.claimable) + amount)

    def _release_bond(self, submission, recipient):
        if submission.get("bond_released"):
            return
        amount = int(submission["bond_atto"])
        self.bond_escrow = u256(int(self.bond_escrow) - amount)
        self._credit(recipient, amount)
        submission["bond_released"] = True

    def _remove_active(self, dossier, submission_id):
        dossier["active_ids"] = [x for x in dossier["active_ids"] if x != submission_id]
        dossier["queue"] = [x for x in dossier["queue"] if x != submission_id]
        if dossier["pending_id"] == submission_id:
            dossier["pending_id"] = ""

    def _close_refund(self, dossier, reason):
        if int(dossier["reward_atto"]) > 0:
            reward = int(dossier["reward_atto"])
            self.reward_escrow = u256(int(self.reward_escrow) - reward)
            self._credit(dossier["sponsor"], reward)
            dossier["reward_atto"] = "0"
        dossier["status"] = "CLOSED_REFUNDED"
        dossier["resolution"] = reason
        dossier["closed_at"] = _iso()
        for sid in list(dossier["active_ids"]):
            submission = self._submission(sid)
            if submission["status"] == "COMMITTED" and _now() >= int(submission["reveal_deadline"]):
                submission["status"] = "UNREVEALED"
                self._release_bond(submission, dossier["sponsor"])
            else:
                submission["status"] = "PROTOCOL_BLOCKED"
                self._release_bond(submission, submission["researcher"])
            submission["settled_at"] = _iso()
            self._save_submission(submission)
        dossier["active_ids"] = []
        dossier["queue"] = []
        dossier["pending_id"] = ""
        self._save_dossier(dossier)

    def _request_witness(self, dossier, request_id, url, claim):
        dossier["pending_id"] = request_id
        dossier["stage_deadline"] = str(_now() + STAGE_WINDOW)
        self._save_dossier(dossier)
        witness = gl.get_contract_at(Address(self.witness_address))
        witness.emit(on="finalized").attest(request_id, str(gl.message.contract_address),
            dossier["question"], dossier["decision_rule"], dossier["source_policy"],
            _json(dossier["evidence"]), url, claim)

    def _request_verdict(self, dossier, request_id, candidate_id=""):
        dossier["pending_id"] = request_id
        dossier["stage_deadline"] = str(_now() + STAGE_WINDOW)
        self._save_dossier(dossier)
        engine = gl.get_contract_at(Address(self.engine_address))
        engine.emit(on="finalized").resolve(request_id, str(gl.message.contract_address),
            dossier["question"], dossier["decision_rule"], dossier["position_a"],
            dossier["position_b"], _json(dossier["evidence"]), candidate_id)

    @gl.public.write.payable
    def open_dossier(self, title: str, question: str, decision_rule: str, position_a: str,
                     position_b: str, source_policy: str, baseline_json: str, closes_at: u256) -> str:
        if not self.configured:
            raise gl.vm.UserError("[EXPECTED] protocol is not configured")
        title = _text(title, "title", 96, 4)
        question = _text(question, "question", 1800, 20)
        decision_rule = _text(decision_rule, "decision rule", 2600, 30)
        position_a = _text(position_a, "position A", 90, 2)
        position_b = _text(position_b, "position B", 90, 2)
        if position_a.lower() == position_b.lower():
            raise gl.vm.UserError("[EXPECTED] positions must differ")
        source_policy = _text(source_policy, "source policy", 1600, 15)
        try:
            baseline = json.loads(baseline_json)
        except Exception:
            raise gl.vm.UserError("[EXPECTED] baseline must be JSON") from None
        if not isinstance(baseline, list) or not 1 <= len(baseline) <= MAX_BASELINE:
            raise gl.vm.UserError("[EXPECTED] baseline must contain 1..4 sources")
        seeds = []
        for index, item in enumerate(baseline):
            url = _text(item.get("url", ""), "baseline URL", 900, 8)
            claim = _text(item.get("claim", ""), "baseline claim", 1200, 8)
            if not url.startswith("https://"):
                raise gl.vm.UserError("[EXPECTED] HTTPS baseline required")
            seeds.append({"id": f"base-{index + 1}", "url": url, "claim": claim})
        reward = int(gl.message.value)
        if not MIN_REWARD <= reward <= MAX_REWARD or not _now() + 3600 <= int(closes_at) <= _now() + 21 * 86400:
            raise gl.vm.UserError("[EXPECTED] invalid reward or closing time")
        dossier_id = "noema-" + str(int(self.next_dossier))
        self.next_dossier = u256(int(self.next_dossier) + 1)
        dossier = {"id": dossier_id, "title": title, "question": question,
            "decision_rule": decision_rule, "position_a": position_a, "position_b": position_b,
            "source_policy": source_policy, "sponsor": str(gl.message.sender_address),
            "status": "BASELINE_WITNESSING", "reward_atto": str(reward),
            "bond_atto": str(max(MIN_BOND, reward // 100)), "created_at": _iso(),
            "closes_at": str(int(closes_at)), "baseline_queue": seeds, "baseline_cursor": 0,
            "evidence": [], "manifest_root": "", "submission_ids": [], "active_ids": [],
            "queue": [], "pending_id": "", "stage_deadline": "", "winner": "",
            "resolution": "", "decisive_ids": [], "closure_basis": "", "closed_at": ""}
        self._save_dossier(dossier)
        self.dossier_ids.append(dossier_id)
        self.deposited = u256(int(self.deposited) + reward)
        self.reward_escrow = u256(int(self.reward_escrow) + reward)
        seed = seeds[0]
        self._request_witness(dossier, f"baseline:{dossier_id}:0", seed["url"], seed["claim"])
        return dossier_id

    @gl.public.write
    def record_attestation(self, request_id: str, result_json: str) -> None:
        if str(gl.message.sender_address).lower() != self.witness_address.lower():
            raise gl.vm.UserError("[EXPECTED] witness callback only")
        result = json.loads(result_json)
        if request_id.startswith("baseline:"):
            _, dossier_id, cursor_text = request_id.split(":")
            dossier = self._dossier(dossier_id)
            if dossier["status"] != "BASELINE_WITNESSING" or dossier["pending_id"] != request_id:
                raise gl.vm.UserError("[EXPECTED] stale baseline callback")
            if result.get("status") != "ATTESTED":
                self._close_refund(dossier, "INVALID_OR_UNAVAILABLE_BASELINE")
                return
            cursor = int(cursor_text)
            seed = dossier["baseline_queue"][cursor]
            dossier["evidence"].append(self._evidence_record(seed["id"], seed["url"], seed["claim"], result, "BASELINE"))
            cursor += 1
            dossier["baseline_cursor"] = cursor
            dossier["pending_id"] = ""
            if cursor < len(dossier["baseline_queue"]):
                seed = dossier["baseline_queue"][cursor]
                self._request_witness(dossier, f"baseline:{dossier_id}:{cursor}", seed["url"], seed["claim"])
            else:
                dossier["status"] = "BASELINE_DECISION"
                dossier["manifest_root"] = _manifest_root(dossier["evidence"])
                self._request_verdict(dossier, f"baseline-verdict:{dossier_id}")
            return
        submission = self._submission(request_id)
        dossier = self._dossier(submission["dossier_id"])
        if submission["status"] != "WITNESS_PENDING" or dossier["pending_id"] != request_id:
            raise gl.vm.UserError("[EXPECTED] stale attestation callback")
        submission["attestation"] = result
        if dossier["status"] != "OPEN" or _now() >= int(dossier["closes_at"]):
            submission["status"] = "STALE"
            self._release_bond(submission, submission["researcher"])
            self._finish_submission(dossier, submission)
        elif result.get("status") == "UNAVAILABLE":
            submission["status"] = "RETRYABLE"
            self._release_bond(submission, submission["researcher"])
            self._finish_submission(dossier, submission)
        elif result.get("status") != "ATTESTED":
            submission["status"] = "REJECTED"
            self._release_bond(submission, dossier["sponsor"])
            self._finish_submission(dossier, submission)
        else:
            submission["status"] = "VERDICT_PENDING"
            candidate = self._evidence_record(submission["id"], submission["url"], submission["claim"], result, "RESEARCH")
            submission["candidate_record"] = candidate
            dossier["evidence"].append(candidate)
            dossier["manifest_root"] = _manifest_root(dossier["evidence"])
            self._save_submission(submission)
            self._request_verdict(dossier, submission["id"], submission["id"])

    def _evidence_record(self, item_id, url, claim, result, kind):
        return {"id": item_id, "kind": kind, "requested_url": url,
            "requested_origin": result.get("requested_origin", ""),
            "source_host": result.get("requested_host", ""),
            "verified_response_origin": result.get("verified_response_origin", ""),
            "transport_origin_verified": bool(result.get("transport_origin_verified", False)),
            "canonical_url": result.get("document_canonical_url", ""),
            "publisher": result.get("document_publisher", ""),
            "published_at": result.get("published_at", ""), "claim": claim,
            "claim_digest": result["claim_digest"], "content_digest": result["content_digest"],
            "observed_at": result["observed_at"], "http_status": result.get("http_status", 0)}

    @gl.public.write
    def record_verdict(self, request_id: str, result_json: str) -> None:
        if str(gl.message.sender_address).lower() != self.engine_address.lower():
            raise gl.vm.UserError("[EXPECTED] engine callback only")
        result = json.loads(result_json)
        if request_id.startswith("baseline-verdict:"):
            dossier = self._dossier(request_id.split(":", 1)[1])
            if dossier["status"] != "BASELINE_DECISION" or dossier["pending_id"] != request_id:
                raise gl.vm.UserError("[EXPECTED] stale baseline verdict")
            if result.get("manifest_root") != dossier["manifest_root"]:
                raise gl.vm.UserError("[EXPECTED] baseline manifest root mismatch")
            dossier["pending_id"] = ""
            if result.get("outcome") != "UNRESOLVED":
                self._close_refund(dossier, "BASELINE_ALREADY_RESOLVES")
            else:
                dossier["status"] = "OPEN"
                dossier["baseline_queue"] = []
                self._save_dossier(dossier)
            return
        submission = self._submission(request_id)
        dossier = self._dossier(submission["dossier_id"])
        if submission["status"] != "VERDICT_PENDING" or dossier["pending_id"] != request_id:
            raise gl.vm.UserError("[EXPECTED] stale verdict callback")
        if result.get("manifest_root") != dossier["manifest_root"]:
            raise gl.vm.UserError("[EXPECTED] verdict manifest root mismatch")
        decisive_ids = result.get("decisive_ids")
        valid_ids = [item["id"] for item in dossier["evidence"]]
        if (not isinstance(decisive_ids, list) or len(decisive_ids) > MAX_DECISIVE_IDS or
                len(decisive_ids) != len(set(decisive_ids)) or
                any(not isinstance(item, str) or item not in valid_ids for item in decisive_ids)):
            raise gl.vm.UserError("[EXPECTED] invalid decisive evidence set")
        submission["verdict"] = result
        if result.get("outcome") == "UNRESOLVED":
            submission["status"] = "ATTESTED_NON_DECISIVE"
            self._release_bond(submission, submission["researcher"])
            self._finish_submission(dossier, submission)
            if len(dossier["evidence"]) >= MAX_EVIDENCE:
                self._close_refund(dossier, "EVIDENCE_CAP_REACHED")
        else:
            if (submission["id"] not in decisive_ids or
                    result.get("counterfactual_outcome") != "UNRESOLVED" or
                    result.get("contribution_required") is not True):
                raise gl.vm.UserError("[EXPECTED] current submission is not necessary for resolution")
            reward = int(dossier["reward_atto"])
            self.reward_escrow = u256(int(self.reward_escrow) - reward)
            self._credit(submission["researcher"], reward)
            self._release_bond(submission, submission["researcher"])
            submission["status"] = "DECISIVE"
            submission["settled_at"] = _iso()
            dossier["reward_atto"] = "0"
            dossier["status"] = "RESOLVED"
            dossier["winner"] = submission["researcher"]
            dossier["resolution"] = result["outcome"]
            dossier["decisive_ids"] = result["decisive_ids"]
            dossier["closure_basis"] = result["basis"]
            dossier["closed_at"] = _iso()
            self._remove_active(dossier, submission["id"])
            self._save_submission(submission)
            for sid in list(dossier["active_ids"]):
                other = self._submission(sid)
                other["status"] = "PROTOCOL_BLOCKED"
                other["settled_at"] = _iso()
                self._release_bond(other, other["researcher"])
                self._save_submission(other)
            dossier["active_ids"] = []
            dossier["queue"] = []
            dossier["pending_id"] = ""
            self._save_dossier(dossier)

    def _finish_submission(self, dossier, submission):
        submission["settled_at"] = _iso()
        self._remove_active(dossier, submission["id"])
        self._save_submission(submission)
        self._save_dossier(dossier)
        self._start_next(dossier)

    def _start_next(self, dossier):
        if dossier["status"] != "OPEN" or dossier["pending_id"] or not dossier["queue"]:
            return
        sid = dossier["queue"][0]
        submission = self._submission(sid)
        if submission["status"] != "QUEUED":
            dossier["queue"].pop(0)
            self._save_dossier(dossier)
            self._start_next(dossier)
            return
        submission["status"] = "WITNESS_PENDING"
        self._save_submission(submission)
        self._request_witness(dossier, sid, submission["url"], submission["claim"])

    @gl.public.write.payable
    def seal_disclosure(self, dossier_id: str, commitment: str) -> str:
        dossier = self._dossier(dossier_id)
        if dossier["status"] != "OPEN" or _now() + REVEAL_WINDOW >= int(dossier["closes_at"]):
            raise gl.vm.UserError("[EXPECTED] dossier is not accepting research")
        if len(dossier["submission_ids"]) >= MAX_LIFETIME_SUBMISSIONS or len(dossier["active_ids"]) >= MAX_ACTIVE:
            raise gl.vm.UserError("[EXPECTED] bounded submission capacity reached")
        if len(dossier["evidence"]) >= MAX_EVIDENCE:
            raise gl.vm.UserError("[EXPECTED] bounded evidence capacity reached")
        if re.fullmatch(r"[0-9a-f]{64}", commitment) is None or commitment in self.commitments:
            raise gl.vm.UserError("[EXPECTED] invalid or duplicate commitment")
        researcher = str(gl.message.sender_address)
        if researcher.lower() == dossier["sponsor"].lower() or int(gl.message.value) != int(dossier["bond_atto"]):
            raise gl.vm.UserError("[EXPECTED] ineligible researcher or incorrect bond")
        sid = "note-" + str(int(self.next_submission))
        self.next_submission = u256(int(self.next_submission) + 1)
        submission = {"id": sid, "dossier_id": dossier_id, "researcher": researcher,
            "commitment": commitment, "status": "COMMITTED", "bond_atto": dossier["bond_atto"],
            "bond_released": False, "created_at": _iso(),
            "reveal_deadline": str(_now() + REVEAL_WINDOW), "url": "", "claim": ""}
        self._save_submission(submission)
        self.commitments[commitment] = sid
        dossier["submission_ids"].append(sid)
        dossier["active_ids"].append(sid)
        self._save_dossier(dossier)
        bond = int(gl.message.value)
        self.deposited = u256(int(self.deposited) + bond)
        self.bond_escrow = u256(int(self.bond_escrow) + bond)
        return sid

    @gl.public.write
    def disclose(self, submission_id: str, url: str, claim: str, salt: str) -> None:
        submission = self._submission(submission_id)
        dossier = self._dossier(submission["dossier_id"])
        if submission["status"] != "COMMITTED" or str(gl.message.sender_address).lower() != submission["researcher"].lower():
            raise gl.vm.UserError("[EXPECTED] disclosure is not available")
        if _now() >= int(submission["reveal_deadline"]):
            raise gl.vm.UserError("[EXPECTED] disclosure window elapsed")
        url = _text(url, "source URL", 900, 8)
        claim = _text(claim, "claim", 1200, 8)
        salt = _text(salt, "salt", 160, 16)
        if not url.startswith("https://") or _commitment(str(gl.message.contract_address), dossier["id"],
                submission["researcher"], url, claim, salt) != submission["commitment"]:
            raise gl.vm.UserError("[EXPECTED] disclosure does not match its seal")
        reservation = _sha(_json({"dossier": dossier["id"], "url": url, "claim": claim}))
        if reservation in self.reservations and self.reservations[reservation]:
            raise gl.vm.UserError("[EXPECTED] evidence packet already reserved")
        self.reservations[reservation] = submission_id
        submission.update({"url": url, "claim": claim, "claim_digest": _sha(claim),
                           "status": "QUEUED", "revealed_at": _iso(), "reservation": reservation})
        dossier["queue"].append(submission_id)
        self._save_submission(submission)
        self._save_dossier(dossier)
        self._start_next(dossier)

    @gl.public.write
    def expire_disclosure(self, submission_id: str) -> None:
        submission = self._submission(submission_id)
        dossier = self._dossier(submission["dossier_id"])
        if submission["status"] != "COMMITTED" or _now() < int(submission["reveal_deadline"]):
            raise gl.vm.UserError("[EXPECTED] disclosure is not expirable")
        submission["status"] = "UNREVEALED"
        self._release_bond(submission, dossier["sponsor"])
        self._finish_submission(dossier, submission)

    @gl.public.write
    def expire_stage(self, dossier_id: str) -> None:
        dossier = self._dossier(dossier_id)
        pending_id = dossier.get("pending_id", "")
        deadline = int(dossier.get("stage_deadline", "0") or 0)
        if not pending_id or deadline == 0 or _now() < deadline:
            raise gl.vm.UserError("[EXPECTED] semantic stage is not expired")
        if pending_id.startswith("baseline:") or pending_id.startswith("baseline-verdict:"):
            self._close_refund(dossier, "BASELINE_STAGE_TIMEOUT")
            return
        submission = self._submission(pending_id)
        if submission["status"] not in ("WITNESS_PENDING", "VERDICT_PENDING"):
            raise gl.vm.UserError("[EXPECTED] pending submission stage not found")
        if submission["status"] == "VERDICT_PENDING":
            # Judgment receives a tentatively appended candidate. Roll it back
            # before continuing so an inconclusive stage never changes history.
            dossier["evidence"] = [item for item in dossier["evidence"] if item["id"] != submission["id"]]
            dossier["manifest_root"] = _manifest_root(dossier["evidence"])
        submission["status"] = "INCONCLUSIVE_TIMEOUT"
        self._release_bond(submission, submission["researcher"])
        self._finish_submission(dossier, submission)

    @gl.public.write
    def expire_dossier(self, dossier_id: str) -> None:
        dossier = self._dossier(dossier_id)
        if dossier["status"] not in ("OPEN", "BASELINE_WITNESSING", "BASELINE_DECISION") or _now() < int(dossier["closes_at"]):
            raise gl.vm.UserError("[EXPECTED] dossier is not expired")
        self._close_refund(dossier, "DEADLINE_ELAPSED")

    @gl.public.write
    def withdraw(self) -> None:
        if not self.native_payouts_enabled:
            raise gl.vm.UserError("[EXPECTED] native payouts are unavailable on this deployment")
        account = gl.message.sender_address
        pending = int(self.pending_outbound[account]) if account in self.pending_outbound else 0
        if pending > 0:
            raise gl.vm.UserError("[EXPECTED] reconcile the existing withdrawal before starting another")
        if account not in self.credits or int(self.credits[account]) == 0:
            raise gl.vm.UserError("[EXPECTED] no credit available")
        amount = int(self.credits[account])
        # Preserve full backing for all escrow and claims before emitting the
        # external EVM message. Failed finalized children are reconciled below.
        liabilities = int(self.reward_escrow) + int(self.bond_escrow) + int(self.claimable)
        if int(self.balance) < liabilities:
            raise gl.vm.UserError("[EXPECTED] Hub is underfunded; recapitalize before withdrawing")
        nonce = int(self.withdrawal_nonce[account]) if account in self.withdrawal_nonce else 0
        withdrawal_id = _sha(_json({"recipient": str(account).lower(), "nonce": nonce, "amount": amount}))
        if withdrawal_id in self.withdrawals:
            raise gl.vm.UserError("[EXPECTED] withdrawal already exists")
        self.credits[account] = u256(0)
        self.claimable = u256(int(self.claimable) - amount)
        self.withdrawn = u256(int(self.withdrawn) + amount)
        self.pending_outbound[account] = u256(int(self.pending_outbound[account]) + amount if account in self.pending_outbound else amount)
        self.pending_outbound_total = u256(int(self.pending_outbound_total) + amount)
        self.withdrawal_nonce[account] = u256(nonce + 1)
        self.latest_withdrawal_id[account] = withdrawal_id
        self.withdrawals[withdrawal_id] = _json({"id": withdrawal_id, "recipient": str(account),
            "amount": str(amount), "status": "PENDING", "created_at": _iso(), "parent_tx": "", "child_tx": ""})
        # EOA recipients are chain-layer accounts. Use the EVM external-message
        # interface documented for EOA transfers, not an IC-to-IC message.
        _EvmRecipient(Address(str(account))).emit_transfer(value=u256(amount), on="finalized")

    @gl.public.write
    def reconcile_withdrawal(self, withdrawal_id: str, parent_tx: str, child_tx: str) -> None:
        """Consensus-replay the finalized StudioNet parent/child receipt pair.

        A credited child settles the withdrawal. A finalized child with
        value_credited=false restores the claim, records the real payout loss,
        and blocks another withdrawal until the Hub is recapitalized.
        """
        if withdrawal_id not in self.withdrawals:
            raise gl.vm.UserError("[EXPECTED] withdrawal not found")
        item = json.loads(self.withdrawals[withdrawal_id])
        if item["status"] != "PENDING" or not child_tx:
            raise gl.vm.UserError("[EXPECTED] withdrawal is not pending")
        parent_tx = _text(parent_tx, "parent transaction", 66)
        child_tx = _text(child_tx, "child transaction", 66)
        if re.fullmatch(r"0x[0-9a-fA-F]{64}", parent_tx) is None or re.fullmatch(r"0x[0-9a-fA-F]{64}", child_tx) is None:
            raise gl.vm.UserError("[EXPECTED] invalid payout transaction hash")
        outcome = _verify_payout_receipts(parent_tx, child_tx, str(gl.message.contract_address),
                                          item["recipient"], int(item["amount"]), item["created_at"])
        if not isinstance(outcome, dict) or outcome.get("outcome") == "UNAVAILABLE":
            raise gl.vm.UserError("[EXPECTED] finalized payout receipt is unavailable; retry reconciliation")
        if outcome.get("parent_id") != parent_tx.lower() or outcome.get("child_id") != child_tx.lower():
            raise gl.vm.UserError("[EXPECTED] payout receipt identity mismatch")
        if outcome.get("outcome") == "PENDING":
            raise gl.vm.UserError("[EXPECTED] payout child is not finalized")
        if outcome.get("outcome") not in ("DELIVERED", "FAILED"):
            raise gl.vm.UserError("[EXPECTED] payout receipts do not match this withdrawal")
        account = Address(item["recipient"])
        amount = int(item["amount"])
        pending = int(self.pending_outbound[account]) if account in self.pending_outbound else 0
        if pending < amount or int(self.pending_outbound_total) < amount:
            raise gl.vm.UserError("[EXPECTED] pending withdrawal accounting mismatch")
        liabilities_before = int(self.reward_escrow) + int(self.bond_escrow) + int(self.claimable)
        assets_before = int(self.balance) + int(self.pending_outbound_total)
        self.pending_outbound[account] = u256(pending - amount)
        self.pending_outbound_total = u256(int(self.pending_outbound_total) - amount)
        if outcome["outcome"] == "DELIVERED":
            item["status"] = "DELIVERED"
        else:
            self.withdrawn = u256(int(self.withdrawn) - amount)
            self._credit(account, amount)
            liabilities_after = int(self.reward_escrow) + int(self.bond_escrow) + int(self.claimable)
            assets_after = int(self.balance) + int(self.pending_outbound_total)
            realized_loss = _realized_payout_loss(amount, liabilities_before, assets_before,
                                                  liabilities_after, assets_after)
            self.payout_loss = u256(int(self.payout_loss) + realized_loss)
            item["status"] = "FAILED_RECREDITED"
            item["credit_restored"] = True
            item["realized_loss_atto"] = str(realized_loss)
        item["parent_tx"] = parent_tx.lower()
        item["child_tx"] = child_tx.lower()
        item["reconciled_at"] = _iso()
        item["receipt_outcome"] = outcome["outcome"]
        self.withdrawals[withdrawal_id] = _json(item)

    @gl.public.write.payable
    def recapitalize_payouts(self) -> None:
        amount = int(gl.message.value)
        if amount <= 0:
            raise gl.vm.UserError("[EXPECTED] recapitalization requires positive GEN")
        required_before = (int(self.reward_escrow) + int(self.bond_escrow) + int(self.claimable)
            + int(self.withdrawn) + int(self.payout_loss) + int(self.recovery_surplus))
        shortfall = max(0, required_before - int(self.deposited))
        surplus = max(0, amount - shortfall)
        self.deposited = u256(int(self.deposited) + amount)
        self.recovery_surplus = u256(int(self.recovery_surplus) + surplus)

    @gl.public.view
    def get_withdrawal(self, withdrawal_id: str) -> dict:
        if withdrawal_id not in self.withdrawals:
            raise gl.vm.UserError("[EXPECTED] withdrawal not found")
        return json.loads(self.withdrawals[withdrawal_id])

    @gl.public.view
    def get_pending_outbound(self, account: str) -> str:
        address = Address(_address(account, "account"))
        return str(int(self.pending_outbound[address]) if address in self.pending_outbound else 0)

    @gl.public.view
    def get_latest_withdrawal(self, account: str) -> dict:
        address = Address(_address(account, "account"))
        withdrawal_id = self.latest_withdrawal_id[address] if address in self.latest_withdrawal_id else ""
        return json.loads(self.withdrawals[withdrawal_id]) if withdrawal_id else {}

    @gl.public.write.payable
    def __on_errored_message__(self) -> None:
        # EOA transfers are external EVM messages and do not call this hook.
        # Internal-message failure recovery is keyed by message sender and exact
        # value. Aggregate pending amounts prevent one request overwriting another.
        account = gl.message.sender_address
        amount = int(gl.message.value)
        expected = int(self.pending_outbound[account]) if account in self.pending_outbound else 0
        if amount == 0 or amount > expected:
            raise gl.vm.UserError("[EXPECTED] unknown failed outbound transfer")
        self.pending_outbound[account] = u256(expected - amount)
        self.pending_outbound_total = u256(int(self.pending_outbound_total) - amount)
        self.withdrawn = u256(int(self.withdrawn) - amount)
        self._credit(account, amount)

    @gl.public.view
    def get_dossier(self, dossier_id: str) -> dict:
        return self._dossier(dossier_id)

    @gl.public.view
    def get_submission(self, submission_id: str) -> dict:
        return self._submission(submission_id)

    @gl.public.view
    def get_submission_for_commitment(self, commitment: str) -> str:
        return self.commitments[commitment] if commitment in self.commitments else ""

    @gl.public.view
    def find_latest_dossier_by_sponsor(self, sponsor: str) -> str:
        target = _address(sponsor, "sponsor").lower()
        for index in range(len(self.dossier_ids) - 1, -1, -1):
            dossier = self._dossier(self.dossier_ids[index])
            if dossier["sponsor"].lower() == target:
                return dossier["id"]
        return ""

    @gl.public.view
    def list_submissions(self, dossier_id: str) -> list:
        dossier = self._dossier(dossier_id)
        return [self._submission(item) for item in dossier["submission_ids"]]

    @gl.public.view
    def list_dossiers(self, offset: u256, limit: u256) -> list:
        start = min(int(offset), len(self.dossier_ids))
        size = min(max(int(limit), 1), MAX_PAGE)
        return [self._dossier(self.dossier_ids[i]) for i in range(start, min(start + size, len(self.dossier_ids)))]

    @gl.public.view
    def get_credit(self, account: str) -> str:
        address = Address(_address(account, "account"))
        return str(int(self.credits[address]) if address in self.credits else 0)

    @gl.public.view
    def get_stats(self) -> dict:
        liabilities = int(self.reward_escrow) + int(self.bond_escrow) + int(self.claimable)
        accounting_right = liabilities + int(self.withdrawn) + int(self.payout_loss) + int(self.recovery_surplus)
        available = int(self.balance) + int(self.pending_outbound_total)
        return {"product": "Noema", "version": VERSION, "chain_id": CHAIN_ID,
            "dossiers": str(len(self.dossier_ids)), "max_evidence_per_dossier": str(MAX_EVIDENCE),
            "max_lifetime_submissions": str(MAX_LIFETIME_SUBMISSIONS),
            "max_decisive_ids": str(MAX_DECISIVE_IDS),
            "native_payouts_enabled": self.native_payouts_enabled,
            "payout_loss": str(int(self.payout_loss)),
            "recovery_surplus": str(int(self.recovery_surplus)),
            "pending_outbound": str(int(self.pending_outbound_total)),
            "payout_recovery_required": str(max(0, liabilities - available)),
            "solvent_ok": available >= liabilities,
            "accounting_ok": int(self.deposited) == accounting_right}
