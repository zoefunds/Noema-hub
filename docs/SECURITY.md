# Security model

## Protected assets

- sponsor reward escrow;
- researcher bonds;
- pull-payment credits;
- the accepted evidence manifest;
- payout-driving verdict records;
- browser-held reveal salts.

## Invariants

- A sponsor cannot submit to their own dossier.
- A dossier cannot open unless every baseline source is attested and the baseline verdict is unresolved.
- A disclosure binds chain, Hub, dossier, researcher, URL, claim and salt.
- A source packet can be reserved only once per dossier.
- Only the configured witness and engine can call their corresponding callbacks.
- Only the configured Hub can request worker execution.
- An attested candidate is judged against exactly one manifest root.
- A resolved verdict names at most 12 existing, unique decisive IDs, includes the current candidate, and is unresolved without it.
- Component addresses have no post-bootstrap setter.
- No administrator can seize funds, replace a verdict, or bypass the queue.
- Rewards and returned bonds first become pull credits; a recipient must explicitly call `withdraw` to initiate the native payout.
- A recipient cannot overwrite an unresolved withdrawal with another. Pending outbound value remains tracked until exact finalized parent/child receipts are reconciled.
- A delivered payout is terminal and cannot be claimed a second time. A verified failed child restores the claim but records any backing loss and blocks further payouts until recapitalization.
- Each finalized parent/child receipt pair is consumed once. Replaying it against the same terminal withdrawal or a different pending withdrawal cannot create another credit.
- Conflicting authenticated support passages cannot produce a decisive payout; consensus remains unresolved and reward escrow remains intact.
- A worker callback (`record_attestation`, `record_verdict`) and `expire_stage` are mutually exclusive on the same stage: once `now >= stage_deadline`, only the timeout path may finalize it, so a late callback can never race a timeout rollback for the same bond and reward.
- `expire_dossier` defers to a submission still legitimately being witnessed or resolved: the sponsor's refund cannot be used to decide that submission's outcome instead of its own evidence. Research-admission deadlines (`closes_at`) and in-flight adjudication deadlines (`stage_deadline`) are checked separately.
- Every submission outcome that completes without contributing evidence to the manifest — `REJECTED`, `RETRYABLE` — forfeits its bond to the sponsor rather than refunding it, because the researcher fully controls the URL and the claim that produced that outcome. Only outcomes the researcher did not choose (`PROTOCOL_BLOCKED`, `INCONCLUSIVE_TIMEOUT`) refund the bond. `closes_at` never factors into this classification at all: every path that moves a dossier away from `OPEN` clears `pending_id` first, so a worker callback that still matches `pending_id` proves the dossier is still `OPEN`, regardless of how long FIFO queueing took to reach it. A timely-disclosed submission is therefore always judged on its actual evidence, never on closing-time queue position.
- `transport_origin_verified` and `provenance_status` are independent assurances. `VERIFIED_DIRECT_RESPONSE` is the only case where transport itself was observed and authenticated; `VERIFIED_CONTENT_ADDRESSED_ORIGIN` reports `transport_origin_verified` as false and relies solely on the requested object's own immutable content-addressed identity. Neither is ever promoted to an authenticated publisher identity or publication time.

## Prompt injection

Contract prompts label all dossier and web content as untrusted data and instruct validators to ignore embedded commands, role changes, system-message imitations, and claimed verdicts. More importantly, consensus compares bounded structured fields rather than accepting free-form reasoning as authority.

## Source limitations

Noema does not trust publisher labels or requested origin as proof. Admission requires authenticated direct-response origin metadata matching the normalized HTTPS URL, HTTP 2xx, full-body inspection, and a verbatim support passage present in those exact bytes. The only alternative is the explicit immutable GitHub API/raw allowlist, which requires matching repository and content-addressed object identity and is labeled separately from direct-response provenance. Missing or conflicting origin metadata, ordinary redirects, oversized bodies and conflicting evidence fail closed.

Temporary source unavailability (including HTTP 429 and 5xx statuses) is treated as retryable rather than a substantive policy rejection, but its bond is credited to the sponsor like any other no-evidence outcome: the researcher chose the source URL, so a source under their own control returning a temporary-looking status must not be a free way to exhaust the dossier's bounded lifetime-submission capacity. Permanent missing-source responses such as 404 are rejected outright on the same terms. A successful-looking body on a non-success status is never accepted as documentary evidence. Dynamic resources can vary between validators. Such instability may prevent consensus. Researchers should prefer first-party records with stable content and durable URLs, since both failure to witness and late disclosure are costly to them, not free.

Noema authenticates only the exact bytes fetched at commitment time — a full-body digest and verbatim support passage — not an independently retrievable snapshot of the source. This is adequate for the content-addressed GitHub fallback, whose object identity is immutable by construction, but an ordinary mutable page's digest is only reproducible for as long as its content is unchanged at that URL. Storing full response bytes for every record would conflict with the bounded-state invariants below, so third-party re-verification of a mutable source is reliable only close to the time of attestation; this is a deliberate, documented trade-off, not an unexamined gap.

A correctly fetched, correctly hashed document is still not proof of the paired claim: a byte-exact record and a semantically misleading claim about it are two different things, and the contract treats them that way. `_normalize` discards every admissibility boolean and forces `REJECTED` the instant a claimed `support_quote` is not found verbatim in the authenticated bytes, regardless of what the model otherwise asserted; `test_misleading_attested_claim_with_quote_absent_from_body_is_rejected` runs the real `SourceWitness` contract end to end against a mocked document and a mocked model response claiming support that is not actually present, and confirms the record is forced to `REJECTED` with every field cleared — `test_attested_claim_with_quote_present_in_body_is_accepted` is its positive control.

GenVM's current web response type (`status`, `headers`, `body` only) never exposes a final URL, redirect chain, or `redirected` flag to the contract at all, on StudioNet or in the direct-mode test harness alike. Consequently `VERIFIED_DIRECT_RESPONSE` — the code path for an ordinary mutable page whose transport layer was actually observed — is correctly implemented for when that runtime capability exists, but is not reachable today: every admissible source in the current release is, in practice, the immutable content-addressed GitHub allowlist. This is a stronger position than "mutable sources are less trusted" — right now they cannot be admitted as decisive evidence at all, which the executable acceptance run above (`noema-1`, both evidence records `VERIFIED_CONTENT_ADDRESSED_ORIGIN`) and the test suite both demonstrate rather than merely assert.

## Denial of service controls

All user text, arrays, pages, queues, lifetime records and retained evidence are bounded. Adjudication is FIFO and serial; a callback for anything but the current queue head is rejected outright, so out-of-order processing cannot be used to reorder payout priority. Each nondeterministic stage has a deadline and public recovery call, and that deadline is mutually exclusive with the matching worker callback — a late callback can never race `expire_stage` for the same outcome. A timed-out verdict removes its tentative candidate before the queue advances. Exhausting the lifetime-submission bound is deterred economically rather than for free: every no-evidence outcome (including source unavailability) forfeits its bond to the sponsor, and the cap is scoped per dossier, so one griefed dossier never blocks research on any other. Exhausting the evidence bound terminates with a sponsor refund instead of trapping escrow.

## Deployment checklist

- confirm chain ID `61999` and Studionet RPC;
- deploy an unconfigured Hub;
- deploy both workers bound to that exact Hub;
- configure the Hub once with both worker addresses;
- inspect all three schemas;
- verify `accounting_ok` and `solvent_ok` before and after an end-to-end flow;
- verify the finalized outgoing child through canonical StudioNet RPC under validator replay, recipient balance increase, Hub credit readback, single-use receipt pair, and duplicate-withdraw protection before reporting a payout as successful;
- execute the conflicting-evidence, candidate-timeout, failed-receipt recredit, receipt-replay, and duplicate-credit state-transition tests;
- exercise a real asynchronous stage timeout and verify exact credit restoration, cleared pending state, and healthy accounting;
- publish addresses and deployment transaction hashes;
- never label a transport redirect chain as verified.
