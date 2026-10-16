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
- independently verified response origin when the runtime exposes one (empty on current StudioNet);
- HTTP status and validator observation time;
- SHA-256 digest of the complete fetched response body;
- SHA-256 digest of the exact accepted claim;
- the complete six-field admissibility verdict.

The Hub derives an ordered manifest root from evidence ID, claim digest, content digest, and source host. A verdict callback is rejected unless its manifest root matches current Hub state. Validators independently compare the final outcome, sufficiency, ordered decisive IDs, and closure-basis digest.

Noema does not claim to obtain a transport-level redirect trace, publisher identity, or final response URL when GenVM does not expose them. Requested provenance is stored separately and `transport_origin_verified=false`; requested data is never promoted to authenticated canonical provenance. Only HTTP 2xx responses can become attested evidence.

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

## Economic flow

1. The sponsor deposits a reward.
2. Each researcher deposits the dossier’s exact bond while sealing a domain-separated commitment.
3. An unavailable source refunds the bond; a rejected disclosure credits it to the sponsor.
4. A valid but non-decisive disclosure refunds the bond and remains in the manifest.
5. A disclosure earns the reward only when it is named in the bounded decisive set and removing it makes the rule unresolved.
6. Expiry and bounded-cap closure credit the remaining reward to the sponsor.
7. Recipients withdraw credits in a separate call when the target network supports contract-to-wallet value delivery.

Every semantic stage has an explicit deadline. After timeout, any caller can release the queue: baseline timeouts refund the sponsor, while research timeouts refund the researcher and roll back any tentatively appended candidate.

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

## Verified Studionet release

- Hub: `0x52282B21156C22d1800d0302Ea1e0FFc4De637BF`
- SourceWitness: `0x48B78b602D42bdA41DdA4ABC11820E5CE34391f7`
- VerdictEngine: `0x272F7f1ab9edd2320c9C5F697E0DC1AA97795745`
- deployed source commit: `623407424e30e5b31daf842c82f3031ae34f8227`
- verified dossier: `noema-1`
- decisive disclosure: `note-1`
- result: `POSITION_A`, `note-1` required, counterfactual `UNRESOLVED`, researcher credited `0.0011 GEN`, accounting invariant true

Native withdrawals use the EVM recipient interface and external finalized value messages. The production UI verifies the child receipt, exact recipient and amount, `value_credited`, the recipient wallet balance delta, and the Hub credit readback before reporting payment. The CLI-originated StudioNet payout proof is recorded in `deployments/studionet-e2e-latest.json`. The browser-wallet dossier creation and baseline flow is recorded separately in `deployments/studionet-browser-wallet-verification.json`; it verifies wallet-funded dossier creation but is not a browser-originated payout proof.

The creation and disclosure forms include one-click real-data examples sourced from the official `openai/codex` repository so evaluators can test the flow without inventing inputs. The deployment source hashes and transaction IDs are in `deployments/studionet.json`; `deployments/e2e-studionet.json` is a verbose runner log and may include historical attempts. Use the concise release record for current acceptance claims.
