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
- canonical fetched URL and source-host publisher identity;
- publication time when the document exposes one;
- HTTP status and validator observation time;
- SHA-256 digest of the complete fetched response body;
- SHA-256 digest of the exact accepted claim;
- the complete six-field admissibility verdict.

The Hub derives an ordered manifest root from evidence ID, claim digest, content digest, and source host. A verdict callback is rejected unless its manifest root matches current Hub state. Validators independently compare the final outcome, sufficiency, ordered decisive IDs, and closure-basis digest.

Noema does not claim to obtain a transport-level redirect trace from GenVM. It records both the requested URL and the canonical fetched URL used by validators, with the source host as publisher identity, making that boundary explicit and auditable.

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
5. A decisive disclosure credits reward and bond to the researcher.
6. Expiry and bounded-cap closure credit the remaining reward to the sponsor.
7. Recipients withdraw credits in a separate call.

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

See [architecture](docs/ARCHITECTURE.md), [security](docs/SECURITY.md), and [deployment](docs/DEPLOYMENT.md) before using the protocol.

## Verified Studionet release

- Hub: `0xe4C8fCeD5Ba04019A4816D7F51Daa3EAacc26E40`
- SourceWitness: `0x2988f0021A834385c9Cf33B7687C8b97B59D3Ea0`
- VerdictEngine: `0x6C3BD278F19AAcbd91b776D7DF8883C01f738d96`
- verified dossier: `noema-1`
- decisive disclosure: `note-1`
- result: `POSITION_A`, researcher credited `0.0011 GEN`, accounting invariant true

The creation and disclosure forms include one-click real-data examples sourced from the official `openai/codex` repository so evaluators can test the flow without inventing inputs. The complete public-network run is preserved in `deployments/e2e-studionet.json`.
