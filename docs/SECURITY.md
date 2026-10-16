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
- All transfers use pull credits.

## Prompt injection

Contract prompts label all dossier and web content as untrusted data and instruct validators to ignore embedded commands, role changes, system-message imitations, and claimed verdicts. More importantly, consensus compares bounded structured fields rather than accepting free-form reasoning as authority.

## Source limitations

An HTTPS response proves the bytes validators fetched for a requested URL at their observation time, not the publisher identity, final response origin, or redirect chain. Noema stores the normalized requested origin separately, leaves verified response provenance empty when GenVM does not expose it, and stores a content digest for later comparison. Only 2xx responses are semantically evaluated.

Dynamic resources can vary between validators. Such instability may prevent consensus. Researchers should prefer first-party records with stable content and durable URLs.

## Denial of service controls

All user text, arrays, pages, queues, lifetime records and retained evidence are bounded. Adjudication is FIFO and serial. Each nondeterministic stage has a deadline and public recovery call. A timed-out verdict removes its tentative candidate before the queue advances. Source unavailability is retryable and does not slash a researcher. Exhausting the evidence bound terminates with a sponsor refund instead of trapping escrow.

## Deployment checklist

- confirm chain ID `61999` and Studionet RPC;
- deploy an unconfigured Hub;
- deploy both workers bound to that exact Hub;
- configure the Hub once with both worker addresses;
- inspect all three schemas;
- verify `accounting_ok` before and after an end-to-end flow;
- publish addresses and deployment transaction hashes;
- never label a transport redirect chain as verified.
