# Verification record

This record distinguishes deterministic local checks, the current source-matched StudioNet release, and historical evidence. A payout is successful only when the Hub's canonical-RPC reconciliation verifies finalized parent/child execution, exact recipient and amount, and the recipient balance delta.

## Local verification

From the repository root (Python 3.12+ and Node.js 20+):

```bash
python -m pip install -r requirements.txt
npm install
npm run ci
```

The current local release check passed 73 direct contract tests, 4 sponsor-key safety tests, and 13 frontend tests, plus TypeScript checking, the optimized frontend build, GenVM linting of all three contracts, `pip check`, and dependency audits with no known vulnerabilities. Coverage includes complete-body inspection past the former 24,000-character limit; strict literal-boolean admissibility parsing; rejected redirects, unsupported publishers/origins, contradictory evidence, malformed replies, and prompt injection; frozen sponsor rules and FIFO handling; conflicting-evidence consensus; deadline rollback; forged/mismatched receipts; and stateful receipt replay and duplicate-credit rejection.

Nine stateful tests in `tests/direct/test_stateful_security.py` were added to close gaps the prior suite left between "the helper function behaves correctly in isolation" and "the deployed contract method behaves correctly end to end":

- **All four `reconcile_withdrawal` outcomes are now run through the live contract method**, not just the `_payout_receipt_outcome` helper. Previously only `FAILED` (recredit) and its replay were exercised statefully:
  - `test_delivered_receipt_settles_withdrawal_without_recrediting` — a genuinely successful payout clears `pending_outbound` and the withdrawal is marked `DELIVERED` without ever touching `credits` (proves the happy path cannot double-pay).
  - `test_forged_or_mismatched_receipt_is_rejected_and_leaves_state_unchanged` — a receipt pair that fails consensus linkage (`INVALID`) reverts and leaves the withdrawal `PENDING`, `pending_outbound` untouched, and `consumed_payout_receipts` unmarked, so a legitimate retry is still possible.
  - `test_unfinalized_receipt_is_rejected_without_mutating_state` — a receipt whose child has not finalized (`PENDING`) reverts without mutating any state.
  - `test_unavailable_rpc_lookup_is_rejected_without_mutating_state` — a StudioNet RPC read failure (`UNAVAILABLE`) is rejected as retryable rather than silently treated as settled.
- **`withdraw()` itself is now exercised statefully**, not just inspected as source text:
  - `test_withdraw_blocks_a_second_pending_withdrawal_for_the_same_recipient` — a second `withdraw()` call while one is still unreconciled reverts, and the newly-arrived credit is left untouched for the next withdrawal.
  - `test_withdraw_refuses_to_send_when_hub_is_underfunded` — the solvency guard reverts before any external value message is emitted when Hub balance cannot cover total liabilities.
- **FIFO reward fairness is now enforced against the live contract, not just grepped for in source**:
  - `test_out_of_order_attestation_callback_violates_fifo_and_reverts` and `test_out_of_order_verdict_callback_violates_fifo_and_reverts` — a callback for anything but the queue head is rejected, and no bond or reward moves as a result.
- **`test_accounting_invariant_holds_through_a_full_loss_and_recapitalization`** runs the full economically consequential sequence end to end: a real backing loss on a failed payout flips `accounting_ok` to `false` and reports the exact `payout_recovery_required`, and `recapitalize_payouts` restores `accounting_ok` to `true` once the shortfall is covered — demonstrating the invariant is load-bearing, not cosmetic.

A second review round closed four further issues, each with its own stateful test:

- **Worker-callback / expire_stage mutual exclusivity.** `record_attestation` and `record_verdict` now reject outright once `now >= stage_deadline` — the exact boundary at which `expire_stage` itself becomes callable — so a late decisive callback can never race a timeout rollback for the same bond and reward. `test_late_attestation_callback_after_deadline_reverts_then_expire_stage_succeeds` and `test_late_verdict_callback_after_deadline_reverts_then_expire_stage_rolls_back` exercise both the rejected late callback and the subsequent successful `expire_stage` call in the same test.
- **`expire_dossier` deferring to in-flight adjudication.** `closes_at` (research admission) and `stage_deadline` (in-flight adjudication) are now checked separately: `expire_dossier` defers with `in-flight adjudication must resolve or expire before dossier closure` whenever a submission is still pending and its own stage has not yet timed out, even once `closes_at` has passed, so a sponsor refund can never decide that submission's outcome by a race. `test_expire_dossier_defers_while_adjudication_is_still_within_its_own_deadline` proves both the deferral and the subsequent successful closure once the stage itself times out.
- **Lifetime-submission exhaustion economics.** `STALE` (disclosed too late to be witnessed before closing) and `RETRYABLE`/`UNAVAILABLE` (the researcher's own chosen source returning a temporary-looking HTTP status) now forfeit the bond to the sponsor instead of refunding it for free, closing the only two outcomes a researcher could previously trigger at zero cost to burn through a dossier's bounded 72-submission lifetime capacity. `test_stale_and_unavailable_callbacks_forfeit_bond_to_sponsor_not_researcher` exercises both paths against the live contract.
- **Provenance semantics.** `transport_origin_verified` is no longer conflated with content-addressed assurance: it is true only for `VERIFIED_DIRECT_RESPONSE` (the transport layer was actually observed and authenticated) and false for `VERIFIED_CONTENT_ADDRESSED_ORIGIN` (no transport metadata was ever observed; the object's own immutable content-addressed identity is the independent assurance instead). `test_attestation_valid_treats_content_addressed_and_direct_response_as_distinct` proves `_attestation_valid` accepts each provenance path only with its own matching value, never the other's.

GitHub Actions is configured in [`.github/workflows/quality.yml`](../.github/workflows/quality.yml). No hosted-green claim is made: on 2026-10-20 GitHub stopped the release-evidence run [`39456409579`](https://github.com/zoefunds/Noema-hub/actions/runs/39456409579) before either job executed because of an owner-controlled billing authorization failure. The workflow-equivalent checks above passed locally; hosted CI must be rerun after the account billing issue is resolved.

## Current source-matched StudioNet release

[`deployments/studionet.json`](../deployments/studionet.json) records a clean StudioNet `61999` deployment from commit `2391ac15d210e8d505cb7bd3c8e08d73788883b3`. The deployer retrieved each deployed contract through GenLayerJS `getContractCode`, required SHA-256 equality with the checked-in source, and checked finalized execution before writing the manifest.

| Contract | Address | Deployed source SHA-256 |
|---|---|---|
| NoemaHub | `0xcBcfF1dc3FD979fb48d65E078Ca7a8fcf98483e4` | `4beaa1487527b6671d14ecdaacc8273ad577a806b3769f85163d24222b1449d0` |
| SourceWitness | `0x9D2CF136821F01369fbBc462F5fE868670c92785` | `ba20fe8715ee1ad1eecd8e6ead0c0ff3f4d58d0d640dc1b88e2dd2e4de06f713` |
| VerdictEngine | `0x22C980402f1bF4D15333aF4CE5002A3f19DC9eA9` | `eb5373a68b165172c18433bb10c48c864e8ccdba935fb64fbd94cfc06a884e9a` |

Deployment transactions are `0x8fbb85ace3d58ec90b4eaaa1d89e3bae77699cbeb4fc8abba6d35c6cfb0d57ca`, `0xcae8b91b3d1d86a5e36ab649250055e4e55c05845e50295950ad1e5a8c20b40a`, and `0x6a64467cbabe93f52479eafe977f0d5356f3f453d04e3135115352b5a6fbbb73`; the immutable worker binding is `0x61200c1f911a2be12ba93a48c5c1080bfac976b46904f64de182886d603ff532`.

## Fresh StudioNet lifecycle

The `freshRedeploymentRun` in [`deployments/e2e-studionet.json`](../deployments/e2e-studionet.json) is the current-release CLI/GenLayerJS record. It resolved `noema-1` as `POSITION_A` using a frozen rule root and a deterministic, authenticated-support closure basis; removing that support makes the result unresolved.

The researcher received `1100000000000000` atto GEN (`0.0011 GEN`). Withdrawal parent `0xa878680d9a22f17e2fc9ff51053660a053e3e32db01474e2a1d0507544b9b4a0` and finalized child `0x1a3fc2e900400c3a8f9961f01621901ff2afa7b91fda2a137dba90e456cc8d63` were reconciled as `DELIVERED`; the Hub credit changed from that amount to zero and the recipient balance rose from `452499999967045000` to `453599999967045000` atto GEN. The record also proves duplicate withdrawal rejection, zero residual sponsor balance, accounting, and solvency.

The timeout artifact [`deployments/studionet-timeout-rollback.json`](../deployments/studionet-timeout-rollback.json) is retained as a real asynchronous StudioNet timeout demonstration, but it belongs to an earlier deployment and is not presented as current-release evidence. Likewise, [`deployments/studionet-browser-wallet-verification.json`](../deployments/studionet-browser-wallet-verification.json) is historical only.

## Browser-wallet status

The current production site is [neoma-hub.vercel.app](https://neoma-hub.vercel.app), deployment `dpl_EFmyYfwdwc4Nszw9U1U7m2PUg8qy`, configured for the current Hub. A browser-wallet account successfully opened current-Hub dossier `noema-2` in finalized transaction `0xcbff89cf95f8886ef66b8c3365e03abef0e7da8c8c07ff3afb1877d0cd3c8bf9`. A later browser audit caught a stale pending seal request before signing; it was canceled, and the actual `neoma-hub` project configuration was corrected and redeployed.

That browser-originated dossier is still `OPEN`. A current-release browser seal, reveal, witness, verdict, reward, withdrawal, and reconciliation sequence has **not** been claimed or recorded. Completing it requires the wallet holder's just-in-time confirmation for the real bond and withdrawal transactions.

## Security boundaries

SourceWitness authenticates bytes, request/response binding, complete-body digest and size, exact support, and allowlisted immutable content-addressed origins. It does not turn an ordinary fetched web page into cryptographic proof of a publisher's identity or publication time; policy requiring those properties rejects the source unless the required origin authentication is available. Redirects, origin conflicts, unsupported publisher claims, and oversized or otherwise unauthenticated decisive material fail closed.

The Vercel receipt endpoint is a UI projection only. The Hub's `reconcile_withdrawal` validates finalized canonical StudioNet parent/child records directly under validator replay, including linkage, sender, recipient, amount, calldata, finality, `value_credited`, and single-use receipt consumption. A verified failure can recredit only once and withdrawals remain blocked when the resulting backing is insolvent.
