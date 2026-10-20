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

## Callbacks

The Hub authenticates callback sender addresses. Worker contracts authenticate the configured Hub for every request. Request IDs are single-use in workers, and Hub-side status checks reject late, duplicate or wrong-stage callbacks. Component addresses are immutable after one-time bootstrap.

Any caller can execute `expire_stage` after its deadline. Baseline timeouts refund the sponsor. Research-stage timeouts refund the researcher, clear the pending slot, and continue FIFO processing. If judgment timed out after tentative append, the candidate is removed and the prior manifest root is restored first.
