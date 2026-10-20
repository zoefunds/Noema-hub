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

## Prompt injection

Contract prompts label all dossier and web content as untrusted data and instruct validators to ignore embedded commands, role changes, system-message imitations, and claimed verdicts. More importantly, consensus compares bounded structured fields rather than accepting free-form reasoning as authority.

## Source limitations

Noema does not trust publisher labels or requested origin as proof. Admission requires authenticated direct-response origin metadata matching the normalized HTTPS URL, HTTP 2xx, full-body inspection, and a verbatim support passage present in those exact bytes. The only alternative is the explicit immutable GitHub API/raw allowlist, which requires matching repository and content-addressed object identity and is labeled separately from direct-response provenance. Missing or conflicting origin metadata, ordinary redirects, oversized bodies and conflicting evidence fail closed.

Temporary source unavailability (including HTTP 429 and 5xx statuses) is treated as retryable and returns the researcher bond; it is not treated as a substantive policy rejection. Permanent missing-source responses such as 404 are rejected. A successful-looking body on a non-success status is never accepted as documentary evidence. Dynamic resources can vary between validators. Such instability may prevent consensus. Researchers should prefer first-party records with stable content and durable URLs.

## Denial of service controls

All user text, arrays, pages, queues, lifetime records and retained evidence are bounded. Adjudication is FIFO and serial. Each nondeterministic stage has a deadline and public recovery call. A timed-out verdict removes its tentative candidate before the queue advances. Source unavailability is retryable and does not slash a researcher. Exhausting the evidence bound terminates with a sponsor refund instead of trapping escrow.

## Deployment checklist

- confirm chain ID `61999` and Studionet RPC;
- deploy an unconfigured Hub;
- deploy both workers bound to that exact Hub;
- configure the Hub once with both worker addresses;
- inspect all three schemas;
- verify `accounting_ok` and `solvent_ok` before and after an end-to-end flow;
- verify the finalized outgoing child through canonical StudioNet RPC under validator replay, recipient balance increase, Hub credit readback, single-use receipt pair, and duplicate-withdraw protection before reporting a payout as successful;
- publish addresses and deployment transaction hashes;
- never label a transport redirect chain as verified.
