# Architecture

## Trust boundaries

Noema divides semantic work into two independent decisions.

1. **Source admissibility:** did a fetched public document establish this exact claim under the sponsor’s published source and time policy?
2. **Dossier sufficiency:** does the ordered set of attested claims now satisfy the precommitted decision rule?

Keeping these questions in separate contracts prevents a plausible source from silently becoming a payout decision.

## Dossier state machine

```text
BASELINE_WITNESSING → BASELINE_DECISION → OPEN
        │                    │             │
        └──────────── refund ┴─────────────┤ deadline / evidence cap
                                           │
                           COMMITTED → QUEUED → WITNESS_PENDING
                                │                     │
                           UNREVEALED       RETRYABLE / REJECTED
                                                      │
                                               VERDICT_PENDING
                                                 │          │
                                   ATTESTED_NON_DECISIVE   DECISIVE
                                                 │          │
                                               OPEN      RESOLVED
```

Only one disclosed note per dossier is adjudicated at a time. FIFO ordering makes payout priority deterministic. Commitments may coexist, but callbacks cannot race two competing manifest versions.

## Provenance packet

The witness fetches the requested HTTPS resource with `gl.nondet.web.get`. It hashes and semantically inspects the complete response body. Sources above the all-content bound are rejected rather than partially inspected. Validators replay both the fetch and prompt, then compare:

- status;
- HTTP status;
- content digest;
- normalized requested origin and host;
- verified response origin only when provided by the transport runtime;
- an exact verbatim support passage and its digest;
- same subject;
- policy compliance;
- direct claim support;
- correct time scope;
- material novelty;
- internal consistency.

The contract deterministically rejects an attestation if its support passage is absent from the fetched bytes. Missing response-origin metadata and any observed redirect fail closed for ordinary sources. A narrowly allowlisted immutable GitHub API/raw object may instead authenticate through exact repository and content-addressed object identity; the resulting packet is explicitly labeled `VERIFIED_CONTENT_ADDRESSED_ORIGIN`. Explanatory prose cannot alter settlement without the compared fields.

`transport_origin_verified` and `provenance_status` are kept as two independent assurances rather than one boolean: `transport_origin_verified` is true only for `VERIFIED_DIRECT_RESPONSE`, where the transport layer's own final URL was actually observed and matched; it is false for `VERIFIED_CONTENT_ADDRESSED_ORIGIN`, which never observes transport metadata at all and instead relies entirely on the requested path's own immutable, content-addressed object identity. The Hub's admissibility check accepts each path only with its own matching value, never the other's — collapsing them would let a content-addressed object be mistaken for an observed, verified host, or vice versa. Neither path, nor any field either produces, ever authenticates a document's claimed publisher or publication time.

## Verdict packet

The Hub freezes sponsor terms at creation into `rules_root`, appends a fully attested candidate, recomputes the ordered manifest root, and calls the engine. The engine reasons from authenticated support passages rather than claim text and returns unresolved on material source conflict. It evaluates both the full manifest and a counterfactual manifest with that candidate removed. Settlement requires a resolved full verdict, an unresolved counterfactual verdict, and the FIFO-current candidate in the unique decisive set.

Each validator compares outcome, sufficiency, the ordered decisive set, and the digest of its closure basis for both decisions. The engine also returns both manifest roots and the counterfactual outcome. The Hub rejects a callback for another root or a candidate-independent result.

## Finite resource model

The lifetime submission counter is the length of a permanently bounded ID vector. Terminal history never restores it. Evidence is likewise bounded. At the evidence ceiling, an unresolved dossier becomes `CLOSED_REFUNDED` with `EVIDENCE_CAP_REACHED`; all pending protocol-blocked bonds are credited to their owners.

This makes worst-case storage and semantic input size calculable:

- up to 72 compact submission records;
- up to 18 evidence packets;
- up to 24 active commitments;
- up to 12 payout-decisive IDs.

The cap is scoped per dossier, so exhausting it never affects any other dossier. Bond forfeiture makes exhausting it costly rather than free: every outcome that completes without contributing evidence to the manifest — `REJECTED`, `STALE` (disclosed too late to be witnessed before closing), `RETRYABLE` (the researcher's own chosen source returned a temporary-looking status), and `UNREVEALED` — credits the bond to the sponsor instead of refunding it, because the URL, claim, and disclosure timing are all the researcher's own choice. Only `PROTOCOL_BLOCKED` (displaced by another submission's resolution) and `INCONCLUSIVE_TIMEOUT` (a genuine protocol-level stage timeout, not an HTTP response the researcher's own source produced) refund the researcher, since neither is attributable to a choice they made. Bond size scales with the dossier's own reward (`max(MIN_BOND, reward // 100)`), so the cost of an exhaustion attempt scales with the reward at stake.

## Callbacks

The Hub authenticates callback sender addresses. Worker contracts authenticate the configured Hub for every request. Request IDs are single-use in workers, and Hub-side status checks reject late, duplicate or wrong-stage callbacks. Component addresses are immutable after one-time bootstrap.

A worker callback and `expire_stage` are mutually exclusive on the same stage: `record_attestation` and `record_verdict` both reject outright once `now >= stage_deadline`, the exact boundary at which `expire_stage` itself becomes callable. This closes a race where a late-arriving decisive verdict and a timeout-driven rollback could otherwise both be able to finalize the same submission, awarding a reward the expiry path was meant to have already reclaimed instead.

Any caller can execute `expire_stage` after its deadline. Baseline timeouts refund the sponsor. Research-stage timeouts refund the researcher, clear the pending slot, and continue FIFO processing. If judgment timed out after tentative append, the candidate is removed and the prior manifest root is restored first.

`closes_at` (research admission) and `stage_deadline` (in-flight adjudication) are also kept distinct at dossier closure: `expire_dossier` defers with `in-flight adjudication must resolve or expire before dossier closure` whenever a submission is still pending and its own stage has not yet timed out, even if `closes_at` has already passed. This prevents a sponsor refund from deciding a submission's outcome by a race instead of its own evidence; the submission must be resolved by its worker callback or by `expire_stage`, in that order, before the dossier itself can close.

## Payout finality and recovery

`withdraw` moves one recipient's credit into a serialized pending-outbound record before emitting the external value message. Neither the browser nor the project-controlled Vercel receipt projection can settle that record. `reconcile_withdrawal` independently retrieves the exact parent and child transactions from canonical StudioNet RPC under validator replay and requires finalized status, exact linkage, Hub sender, recipient, amount, withdrawal calldata, creation second, and boolean `value_credited`.

A delivered child consumes its parent/child receipt pair and terminates the withdrawal. A finalized failed child consumes the same pair, restores credit once, and records any newly realized backing deficit. The recipient cannot initiate another payout while an earlier outbound value remains pending, and a consumed pair cannot settle another withdrawal. This keeps chain delivery evidence and Hub accounting in one authenticated state transition.

## Executable assurance

Direct contract tests execute the VerdictEngine leader and validator on conflicting authenticated support passages, then execute the Hub's economically non-decisive callback. Separate stateful tests execute candidate rollback after a verdict-stage deadline and failed-child reconciliation twice to prove single recredit and receipt replay rejection. The public-network record complements these deterministic tests with an actual asynchronous baseline child that remained pending through the full 1,800-second StudioNet window and was recovered by `expire_stage`.
