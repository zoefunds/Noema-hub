# Review response: evidence, payout finality, and fair settlement

This record maps the review's **More Information Requested** findings to the current Noema implementation, test suite, documentation, and StudioNet evidence. It is explicit about what is proven, what fails closed, and what remains an operational limitation.

## Scope and current deployment

The canonical StudioNet manifest is [`deployments/studionet.json`](deployments/studionet.json). It records the current Hub, SourceWitness, and VerdictEngine addresses and an exact source SHA-256 for each deployed contract. The local hashes match those manifest values. Historical E2E material is retained only as evidence and is labeled `HISTORICAL_SUPERSEDED`; it is not a client configuration source.

The changes covered here do not modify deployed contract source. Consequently, they do not require a new deployment or a new on-chain E2E run. The current StudioNet payout record remains the source-matched live evidence; see [`docs/VERIFICATION.md`](docs/VERIFICATION.md).

## 1. Complete source inspection and claim-to-content binding

### Finding

The former 24,000-character inspection boundary could allow a decisive claim to rely on content that had not been completely inspected. A claim also needed a binding to independently replayed source content rather than claim text alone.

### Resolution

`SourceWitness` reads the complete response byte body, computes its SHA-256, and either inspects all of it or rejects it. `MAX_SOURCE_BYTES` is now 120,000; a larger response is returned as `SOURCE_TOO_LARGE` with the explicit message that partial inspection is forbidden. The limit bounds computation without silently truncating documentary evidence.

An attested claim requires a nonempty, bounded verbatim `support_quote`. The contract checks that quote against the complete authenticated body before accepting it. If the quote is missing from the bytes, all admissibility fields are cleared and the record becomes `REJECTED`, even if a model otherwise said the claim was supported.

The Hub commits every accepted evidence record into the ordered manifest root: `rules_root`, evidence ID, requested origin, claim digest, content digest, support digest, source size, HTTP status, and verified provenance. The VerdictEngine receives that manifest and the frozen `rules_root`; callbacks with a mismatched rules or manifest root are rejected. Explanatory claim text therefore cannot substitute for the committed source bytes and support passage.

### Regression evidence

- `test_source_witness_rejects_oversized_sources_instead_of_partially_inspecting_them`
- `test_misleading_attested_claim_with_quote_absent_from_body_is_rejected`
- `test_attested_claim_with_quote_present_in_body_is_accepted`
- `test_attestation_valid_treats_content_addressed_and_direct_response_as_distinct`

## 2. Provenance, publisher claims, redirects, and conflicting evidence

### Finding

Requested URLs, publisher labels, or model assertions must not be treated as authenticated provenance. Redirects and unavailable transport provenance must fail closed.

### Resolution

Only credential-free HTTPS requests are accepted. For an ordinary direct response, the final URL must be available, normalize exactly to the requested URL, and have no redirect history or redirect flag. Missing final-origin data, a nonmatching final URL, unsafe response origin, or any observed redirect is rejected.

StudioNet currently does not expose final-URL/redirect metadata to the contract. Therefore ordinary mutable sources cannot be decisive on the current network. The sole deliberate fallback is an allowlist for immutable, content-addressed GitHub API/raw object paths. It is marked `VERIFIED_CONTENT_ADDRESSED_ORIGIN`, distinct from `VERIFIED_DIRECT_RESPONSE`; it does **not** assert verified transport hosting, publisher identity, canonical URL, or publication time. Unsupported publisher and origin claims are cleared rather than promoted to evidence.

The engine returns `UNRESOLVED` on material conflict. An unresolved result is economically non-decisive: no research reward is released solely because conflicting evidence exists.

### Regression evidence

- `test_source_witness_fails_closed_when_origin_or_redirect_cannot_be_authenticated`
- `test_response_provenance_accepts_only_an_exact_direct_https_origin`
- `test_conflicting_authenticated_quotes_execute_consensus_as_unresolved`
- `test_conflicting_evidence_consensus_is_economically_non_decisive`

## 3. Independent payout finality and recovery

### Finding

The project-controlled Vercel gateway cannot decide whether GEN was delivered or whether a failed transfer should be recredited.

### Resolution

`withdraw` creates a serialized `PENDING` outbound record. The Vault may observe a parent transaction and child transfer for user feedback, but it then submits `reconcile_withdrawal`. Inside the Hub, validators independently replay canonical StudioNet RPC reads for the exact parent and child IDs.

Settlement requires both records to be finalized and to match the exact IDs, child-to-parent linkage, recipient-to-Hub withdrawal parent sender/recipient, creation time, encoded `withdraw` calldata, recipient, exact amount, child delivery signal (`value_credited`), and single-use receipt-pair consumption.

Only a verified delivered child records `DELIVERED` and clears pending-outbound accounting. A finalized failed child records `FAILED_RECREDITED`, restores the credit once, records realized backing loss, and may require recapitalization before a further withdrawal. RPC unavailability and nonfinal receipts leave the withdrawal pending and retryable; neither causes an unsupported settlement.

The Vercel endpoint remains a UI projection only. It is not consulted as a settlement authority.

### Regression evidence

- `test_delivered_receipt_clears_pending_and_allows_a_later_earned_credit_to_withdraw`
- `test_failed_receipt_recredits_once_and_receipt_replay_cannot_duplicate_credit`
- `test_forged_or_mismatched_receipt_is_rejected_and_leaves_state_unchanged`
- `test_unfinalized_receipt_is_rejected_without_mutating_state`
- `test_unavailable_rpc_lookup_is_rejected_without_mutating_state`
- `test_withdraw_blocks_a_second_pending_withdrawal_for_the_same_recipient`

The current StudioNet evidence records a finalized delivered child, a `DELIVERED` reconciliation, zero remaining withdrawal credit, the exact wallet balance increase, healthy accounting/solvency, and duplicate-settlement rejection. Transaction identifiers and exact values are in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) and [`deployments/e2e-studionet.json`](deployments/e2e-studionet.json).

## 4. Frozen sponsor rules, FIFO fairness, and consequential consensus

### Finding

Sponsor terms must be auditable and immutable after opening a dossier. Payouts must not be reordered by callbacks or penalize a timely researcher because a FIFO queue outlives `closes_at`. Consensus must have economic consequences.

### Resolution

At creation, the Hub hashes the title, question, decision rule, positions, source policy, reward, closing time, and baseline commitments into `rules_root`. Evidence is appended in order and committed as `manifest_root`. The Hub rejects a verdict unless both roots match current state.

The queue head is the only submission that can be attested or resolved; out-of-order callbacks revert. `closes_at` governs admission of new seals, not the merits of a submission already disclosed and queued on time. Stage deadlines and callbacks are mutually exclusive, so a late callback cannot race timeout recovery.

For a reward to settle, the full verdict must be resolved, the current submission must be in the unique decisive set, and the counterfactual manifest without it must be `UNRESOLVED`. An unresolved conflict is non-decisive and does not receive the reward. This makes validator consensus consequential to escrow accounting rather than advisory prose.

### Regression evidence

- `test_out_of_order_attestation_callback_violates_fifo_and_reverts`
- `test_out_of_order_verdict_callback_violates_fifo_and_reverts`
- `test_queued_submission_witnessed_after_closes_at_is_not_penalized_for_queue_delay`
- `test_decisive_settlement_still_pays_full_reward_after_closes_at_from_queue_delay`
- `test_fifo_queue_of_submissions_disclosed_before_closure_drains_fairly`
- `test_candidate_independent_verdict_cannot_receive_reward`
- `test_accounting_invariant_holds_through_a_full_loss_and_recapitalization`

## Documentation and verification status

The corresponding protocol documentation is maintained in:

- [`README.md`](README.md) — protocol summary and public lifecycle;
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — commitments, provenance, adjudication, and payout state transitions;
- [`docs/SECURITY.md`](docs/SECURITY.md) — fail-closed boundaries and researcher-facing temporary-source bond policy;
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — canonical manifest, current StudioNet evidence, and historical-release boundaries;
- [`docs/VERIFICATION.md`](docs/VERIFICATION.md) — test inventory, live evidence, and disclosed limits.

Current local verification command results:

```
PYTHONPATH=. pytest -q tests/direct     # 80 passed
npm --prefix frontend test              # 13 passed
npm --prefix frontend run typecheck     # passed
npm --prefix frontend run build         # passed
```

## Explicit limitations

- A mutable ordinary web source is intentionally not admissible today because StudioNet does not expose authenticated final-URL or redirect metadata.
- Full source bytes are not permanently stored on-chain; the immutable commitment is the full-body digest plus support passage and provenance fields.
- The production browser UI has not independently performed a complete injected-wallet seal-to-withdrawal lifecycle. The source-matched StudioNet E2E run provides the on-chain settlement evidence, while browser-wallet creation is documented separately.
- Hosted CI remains subject to the documented GitHub account billing lock; local equivalent checks above are current and passing.
