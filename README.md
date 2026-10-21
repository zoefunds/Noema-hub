# Noema

Noema is a GenLayer-native public research protocol. A sponsor funds a tightly framed question, defines two mutually exclusive positions, supplies an admissible-source policy, and anchors an initially insufficient baseline. Researchers privately seal leads, disclose them after reservation, and earn the reward only when their source makes the disclosed rule decidable.

Live application: [neoma-hub.vercel.app](https://neoma-hub.vercel.app)

The protocol is designed for questions that deterministic contracts cannot answer by reading chain state: public records, release artifacts, regulatory notices, scientific registries, signed reports, and other live web evidence.

## What makes a Noema dossier

A valid dossier has:

- one falsifiable public question with a subject and time or version boundary;
- two mutually exclusive positions;
- an explicit decision rule that permits an unresolved result;
- an admissible-source policy;
- one to four baseline sources that validators first witness and confirm are insufficient;
- a reward and deterministic closing time.

Sponsor intent cannot substitute for the published rule. Missing facts remain unresolved.

## Contract system

```text
NoemaHub
  ├── owns rewards, bonds, commitments, queues, limits and pull credits
  ├── SourceWitness
  │     fetches each source and consensus-binds provenance + validity
  └── VerdictEngine
        applies the rule to the exact attested manifest and returns
        outcome + decisive IDs + consensus-bound closure basis
```

`NoemaHub` is the only economic contract. `SourceWitness` cannot move funds or decide an outcome. `VerdictEngine` never fetches unverified sources and cannot alter the evidence manifest. Both worker contracts are permanently bound to the Hub at deployment.

## Durable provenance

Every accepted record persists:

- requested URL and requested host;
- normalized requested URL, requested host and requested origin;
- independently verified response origin; evidence fails closed when the runtime cannot supply it;
- HTTP status and validator observation time;
- SHA-256 digest of the complete fetched response body;
- SHA-256 digest of the exact accepted claim;
- the exact verbatim support passage and its SHA-256 digest;
- the complete six-field admissibility verdict.

The Hub freezes the sponsor's complete rules into `rules_root` and derives an ordered manifest root from that root plus each evidence record's claim, content, support-passage and verified-origin digests. A verdict callback is rejected unless both roots match current Hub state.

Noema never promotes a requested host, document self-claim, or publisher label to authenticated provenance, and it never promotes verified hosting to authenticated publisher identity either — no record ever claims to prove who published a document or when. Normally, a successful response must expose an exact direct final URL matching the normalized request; this is the only case where `transport_origin_verified` is true, because it is the only case where the transport layer itself was actually observed and authenticated. The sole fallback is an explicitly allowlisted immutable GitHub API/raw object whose repository and object identifier are content-addressed and mutually consistent; it receives the distinct `VERIFIED_CONTENT_ADDRESSED_ORIGIN` label and reports `transport_origin_verified` as false, because no final-URL transport metadata was ever observed — the object's own content-addressed identity is a separate, independent assurance, and the two are never conflated into a single boolean. Missing or conflicting origin metadata, ordinary redirects, non-2xx responses, oversized sources and support passages absent from the complete fetched bytes all fail closed.

Both accepted provenance paths authenticate only the exact bytes fetched at commitment time; Noema stores their full-body SHA-256 digest and verbatim support passage, not an independently retrievable snapshot of the source itself. For an ordinary mutable page (`VERIFIED_DIRECT_RESPONSE`), the digest is reproducible only for as long as the page's content stays the same at that URL — unlike `VERIFIED_CONTENT_ADDRESSED_ORIGIN`, whose object identity is immutable by construction. Archiving full response bytes for every record would conflict with the bounded-state invariants in the next section, so this is a deliberate, documented trade-off rather than an unexamined gap: a dossier's historical digests remain cryptographically binding evidence even if the live page later changes, but third-party re-fetch verification of a mutable source is only reliable close to the time of attestation.

## Bounded state and liveness

Limits are protocol invariants rather than UI policy:

| Resource | Per dossier limit | Terminal behavior |
|---|---:|---|
| Baseline records | 4 | creation rejected |
| Concurrent disclosures | 24 | new seal rejected |
| Lifetime disclosures | 72 | new seal rejected |
| Retained attested evidence | 18 | unresolved dossier closes and refunds |
| Decisive evidence IDs | 12 | verdict rejected |

Terminal submissions do not reopen lifetime capacity. This keeps storage, queue processing, prompt size, and read cost bounded for the dossier’s entire life. If all 18 evidence slots are used without a resolution, the remaining sponsor reward is returned through pull credit rather than leaving an unfinishable dossier open.

The bond deters exhausting that permanent per-dossier capacity for free. Bond size scales with the reward (`max(MIN_BOND, reward // 100)`), so burning through all 72 lifetime slots on one dossier costs at least 72 bonds at that dossier's own reward-proportional rate, and splitting an attack across many wallets (Sybil) does not lower that total cost — each wallet still has to post its own full bond per attempt, so the aggregate GEN at risk is unchanged by how many addresses share it. Every outcome that completes without contributing usable evidence to the manifest — an outright rejection, an undisclosed seal, and a source that returns a temporary-looking HTTP status — forfeits its bond to the sponsor, because the URL and the claim are the researcher's own choice and neither is falsifiable from chain state alone. `closes_at` itself never factors into this: it only gates whether a *new* disclosure may be sealed, never how an already-disclosed, already-queued submission's eventual witnessing is classified, so FIFO processing delay can never cost a timely researcher their bond. Only a submission that is displaced by another submission's resolution (`PROTOCOL_BLOCKED`) or lost to a genuine protocol-level stage timeout (`INCONCLUSIVE_TIMEOUT`) refunds the researcher, since neither is something the researcher chose or controlled. Because the cap is scoped per dossier, exhausting one dossier never blocks research on any other, and the sponsor's reward is always fully recovered through `expire_dossier`; the cost of an exhaustion attempt falls on the attacker's bonds, its blast radius is limited to the one dossier being attacked, and queue saturation (at most `MAX_ACTIVE = 24` concurrent disclosures, processed strictly in order) delays rather than permanently displaces a legitimate researcher, since the queue keeps draining once any submission ahead of them settles.

## Economic flow

1. The sponsor deposits a reward.
2. Each researcher deposits the dossier’s exact bond while sealing a domain-separated commitment.
3. A rejected disclosure and a source returning a temporary-looking HTTP status both forfeit the bond to the sponsor — each is a choice fully within the researcher's own control. A disclosure that was timely but is only witnessed after the dossier closes, purely from FIFO queue delay, is never penalized for that delay: it is judged on its actual evidence instead.
4. A valid but non-decisive disclosure refunds the bond and remains in the manifest.
5. A disclosure earns the reward only when it is named in the bounded decisive set and removing it makes the rule unresolved.
6. Expiry and bounded-cap closure credit the remaining reward to the sponsor.
7. Recipients withdraw credits in a separate call when the target network supports contract-to-wallet value delivery.

Every semantic stage has an explicit deadline, and that deadline is mutually exclusive with the matching worker callback: once it has elapsed, `record_attestation`/`record_verdict` reject the callback outright, and only `expire_stage` may act, so a late callback can never race a timeout for the same bond and reward. Research-admission deadlines (`closes_at`) and in-flight adjudication deadlines (`stage_deadline`) are also kept distinct: `expire_dossier` defers to a submission still legitimately being witnessed or resolved rather than refunding the sponsor out from under it. After timeout, any caller can release the queue: baseline timeouts refund the sponsor, while research timeouts refund the researcher and roll back any tentatively appended candidate.

At every deterministic transition:

```text
deposited = reward escrow + bond escrow + claimable credits + withdrawn
```

## Repository map

```text
contracts/
  noema_hub.py          lifecycle, bounded storage and settlement
  source_witness.py     live-web provenance and admissibility
  verdict_engine.py     manifest-bound resolution
  domain.py             pure deterministic helpers
frontend/
  app/                  Next.js interface
  components/           Noema design system
  lib/                  wallet, commitment and contract types
tests/direct/           deterministic invariants and scale bounds
deploy/deployNoema.ts   secure three-contract bootstrap
docs/                   architecture, security and operations
```

## Local development

Requirements: Python 3.12+, Node.js 20+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest tests/direct -q

npm install
npm --prefix frontend install
npm run test:ui
npm run typecheck
npm run build
```

Copy `.env.example` to `frontend/.env.local` after deployment.

## Network

The release configuration targets GenLayer Studionet only:

- chain ID: `61999`
- RPC: `https://studio.genlayer.com/api`
- explorer: `https://explorer-studio.genlayer.com`
- wallet: injected EIP-1193 provider

See [architecture](docs/ARCHITECTURE.md), [security](docs/SECURITY.md), [deployment](docs/DEPLOYMENT.md), and the [verification record](docs/VERIFICATION.md) before using the protocol.

## Testing from the frontend

Both forms that take free-text input have a one-click autofill with real, detailed, contract-accepted data, so anyone with a funded Studionet wallet can exercise the full lifecycle without composing their own dossier:

- **Dossier creation** (`/field/new`) — "Load verified example ↘" fills every field: title, question, both positions, decision rule, source policy, reward, and closing window, plus **two** baseline sources (demonstrating multi-baseline support, not just the minimum of one). Both baseline sources are real, live, immutable GitHub objects (a Git tree and a Git commit from `openai/codex`, addressed by their exact 40-character SHA) that the contract's content-addressed provenance fallback accepts, and both are genuinely insufficient to decide the question on their own — exactly what `open_dossier` requires of a baseline.
- **Research disclosure** (on any open dossier's page) — "Load real license evidence ↘" fills the source URL and claim with the exact immutable `raw.githubusercontent.com` object and verbatim text that decisively resolves the example dossier above: the official `openai/codex` `LICENSE` file at that same commit, which explicitly declares Apache License 2.0.

Because the evidence-reservation key is scoped to `(dossier, url, claim)`, any number of testers can use the *same* autofilled values concurrently on their *own* freshly created dossiers without colliding with each other. The pairing is the same decisive public-source example already used for the verified Studionet release below, so it is known to resolve end to end: baseline witnessing leaves the dossier open, research disclosure attests and settles it as `POSITION_A`, and the disclosing researcher is credited the reward.

## Verified Studionet release

- Hub: `0xB300efF2985bFd06d01D014c8f9EFD502726D76C`
- SourceWitness: `0x84aaab3A1e777F119ac7d3267F0765f647D5d4E0`
- VerdictEngine: `0x0319324A6157DE1b6385DcCd7115593a9D964c72`
- source-matched release commit: `396ec24b77f5e635df6a1cfb962f4ad128745420`; exact deployed/local SHA-256 equality was independently read back for all three contracts
- verified dossier: `noema-1`
- decisive disclosure: `note-1`
- result: `POSITION_A`, `note-1` required, counterfactual `UNRESOLVED`, researcher credited `0.0011 GEN`, withdrawn and reconciled `DELIVERED`, accounting and solvency invariants true before and after
- production frontend: [neoma-hub.vercel.app](https://neoma-hub.vercel.app), deployment `dpl_BCuXM8LYuggQ3J2KXW6WZ2vbtAMo`

Native withdrawals use the EVM recipient interface and external finalized value messages. The Hub—not the Vercel gateway—fetches canonical StudioNet parent and child receipts under validator replay and verifies finality, linkage, sender, recipient, exact amount, calldata, timestamp, `value_credited`, and single-use receipt consumption before delivery or one-time recredit. The current source-matched CLI/GenLayerJS StudioNet proof is recorded in `deployments/e2e-studionet.json`; older artifacts, including the prior release's contracts (`2391ac15d210e8d505cb7bd3c8e08d73788883b3`, Hub `0xcBcfF1dc3FD979fb48d65E078Ca7a8fcf98483e4`), are explicitly historical and superseded. Executable tests now run conflicting-evidence consensus, economically non-decisive Hub settlement, stateful candidate-verdict timeout rollback, deadline-exclusivity races, exhaustion-economics bond forfeiture, and stateful failed-receipt replay/duplicate-credit rejection.

The previous release's timeout lifecycle funded `noema-2`, recorded its emitted SourceWitness child, waited through the actual 1,800-second StudioNet deadline, and finalized `expire_stage` as `0x0498f234793d69aa30db3d09a7f71d3014ee585fa4a9a314b0e39f5f73b7c6aa`. Readback proved `BASELINE_STAGE_TIMEOUT`, zero remaining reward escrow, exact `0.001 GEN` sponsor-credit restoration, and healthy accounting. That run targets the superseded contracts above; a current-release timeout acceptance run has not yet been recorded, since reproducing it requires a real, unshortened 1,800-second wait.

The creation and disclosure forms include one-click real-data examples sourced from the official `openai/codex` repository; dossier creation now autofills two real baseline sources. The frontend stores the researcher address, transaction state, and an exportable recovery packet for every sealed disclosure; it refuses reveal from a different wallet. The deployment source hashes and transaction IDs are in `deployments/studionet.json`; `deployments/e2e-studionet.json` is the current complete CLI lifecycle record, produced in the same run that deployed these contracts. The live production site was checked by browser against this exact Hub: the homepage, dossier listing, `noema-1` detail page, creation form (including its autofill), protocol notes, and vault page all render correctly; a browser-driven wallet-signing walkthrough (seal/reveal/withdraw clicked through the UI) was not performed for this release, since that needs a real wallet extension rather than a scripted signer.
