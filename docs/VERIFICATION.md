# Verification record

This document separates deterministic checks from public-network evidence. A transaction counts as a successful payout only when its finalized execution result, child transfer, wallet balance delta, and authoritative Hub state all agree.

## Reproduce the local checks

Run from the repository root with Python 3.12+ and Node.js 20+:

```bash
python -m pip install -r requirements.txt
python -m pytest tests/direct -q
npm install
npm run test:sponsor-key
npm run test:ui
npm run typecheck
npm run build
```

The latest verified local run passed 43 direct contract tests, 4 sponsor-key safety tests, and 13 frontend tests. Frontend TypeScript checking and optimized production build also passed. Contract coverage includes authenticated callbacks, current-candidate necessity and counterfactual resolution, the executable 12-ID decisive bound, temporary HTTP 429/503 classification, permanent missing-source handling, valid-looking document bodies on unsuccessful responses, retryable bond return on source unavailability, manifest-root parity, timeout recovery, queue and lifetime bounds, serialized pending withdrawals, payout-loss accounting, and exact parent/child payout receipt matching.

The GitHub Actions workflow is `.github/workflows/quality.yml`. Run [`38902347465`](https://github.com/zoefunds/Noema-hub/actions/runs/38902347465), triggered by commit `ebbc36c803efe6a2ca335930e89ef5ef8b71abef`, failed after 3 seconds before starting either job; both GitHub annotations state that the account is locked due to a billing issue. The preceding run for `a93db04d6312e98ac4d4f97f5454f65ce54a6986` (`38900526991`) had the same result. No hosted green result is claimed. Local workflow-equivalent checks passed as listed above. A hosted green run still requires the repository owner to resolve the account billing lock.

## Current StudioNet deployment

The deployed release source commit is `623407424e30e5b31daf842c82f3031ae34f8227`. The authoritative manifest is [`deployments/studionet.json`](../deployments/studionet.json). It records these StudioNet chain 61999 contracts and exact source-hash matches retrieved through GenLayerJS `getContractCode`:

| Contract | Address | Deployed source SHA-256 | Match |
|---|---|---|---|
| NoemaHub | `0x52282B21156C22d1800d0302Ea1e0FFc4De637BF` | `cdbc1a23af6a2b60b6a4ed3030dfb11bd12ee05109df6b9b6cf4d758f0b9ce79` | yes |
| SourceWitness | `0x48B78b602D42bdA41DdA4ABC11820E5CE34391f7` | `0f4ef7d4cc9b7b73ac98bed4d207b1240a1f0854f775e30b874e8e520b376a33` | yes |
| VerdictEngine | `0x272F7f1ab9edd2320c9C5F697E0DC1AA97795745` | `7085da39128709f465d30b3fce9988b21fecff9b17d2edc624305e5a625ce026` | yes |

The deployed contract files have no changes between that source commit and the current repository `HEAD`. The concise StudioNet execution record is [`deployments/studionet-e2e-latest.json`](../deployments/studionet-e2e-latest.json); the larger `deployments/e2e-studionet.json` is a historical, verbose harness log and is not the source of current deployment addresses.

## Real StudioNet research and payout run

The concise record documents a completed CLI/GenLayerJS run against the deployed Hub, using official OpenAI Codex public sources:

- dossier `noema-1` asks whether the default-branch root `LICENSE` expressly declares Apache License 2.0;
- baseline Git tree request: `https://api.github.com/repos/openai/codex/git/trees/main`, HTTP 200, body digest `71d883efa8d69e4f94099f7aebbcea35f098f603ca2567502878493887427497`;
- decisive source: `https://raw.githubusercontent.com/openai/codex/main/LICENSE`, HTTP 200, body digest `d17f227e4df5da1600391338865ce0f3055211760a36688f816941d58232d8dc`;
- outcome `POSITION_A`, decisive evidence `note-1`, and counterfactual without `note-1` `UNRESOLVED`; manifest root `98d5ee42a07d403772477c9f4477f81e0df648ef68ba748ef76f76e6c01ceeb6`;
- sponsor funding `0xc8fdf195264919e64404895b8597ae719c4d46fdcfa8a1c54878a84ea35188ab`; dossier opening `0x08918cdf05c07eb8afb588517d88d9523a14cef68c4ab42aaa730b0d9ea30158`; commitment seal `0x4c78cf9747969dd0add21924df553d38bfdbfeb8de2b418b50165b0d13d14bac`; disclosure `0x53630d5c9944e4ea0793e89bf10cf1edbb934e1e008dba988e66f4599e1f9c83`;
- reward plus returned bond credited to the researcher: `1100000000000000` atto GEN (`0.0011 GEN`);
- withdrawal parent `0x05274e66eb4093cb16e48b1a7b8f3080bf92ff185a689ca91b67300456739120`; finalized child `0xc97a20a6510b2597b37545acecc77f4e8de9334c54faa77cc07727f5f2be2661`, recipient `0x7401c129EDfc26E68FE19309fE461eb3Db1058Eb`, exact value `1100000000000000` atto GEN, `value_credited=true`;
- recipient balance moved from `999000000999876277587324887999999998992` to `999000000999876277587325987999999998992` atto GEN, an exact increase of `1100000000000000`;
- reconciliation `0x610f43f82eb842592891fa3554d2ff73f728d705de3bd3eb1e3ae2705ea5a829` read back `DELIVERED` with the exact parent and child IDs; Hub credit moved from `1100000000000000` to `0`; accounting and solvency remained true; duplicate withdrawal was rejected;
- a separate finalized transaction returned the temporary sponsor's unused `0.002 GEN`; it is not part of the recipient's payout delta.

The recorded research-and-payout run above was initiated with the GenLayerJS CLI, not from the browser wallet. The separate browser-wallet run is recorded in [`deployments/studionet-browser-wallet-verification.json`](../deployments/studionet-browser-wallet-verification.json). Studio Explorer confirms the wallet-funded `open_dossier` call, the baseline attestation/unresolved-verdict callback chain, and a successful `seal_disclosure` returning `note-2`. The next `disclose` call finalized as a transaction but its GenVM execution reverted with `[EXPECTED] disclosure does not match its seal`; this is a failed application operation, not a successful disclosure. The production page readback remained `OPEN`, with one baseline evidence record, zero disclosures, a 10 GEN reward, and a 0.1 GEN bond. Consequently, this browser run provides no researcher reward attribution, withdrawal, or payout evidence. The distinct CLI/GenLayerJS payout remains the only successful withdrawal proof currently published.

This browser evidence proves wallet-originated dossier funding/creation and baseline processing, but it does not prove a browser-originated research reward or withdrawal. No disclosure or withdrawal hash was provided in this browser run. The separate CLI payout record remains the only current end-to-end reward-to-EOA proof; keep these two evidence scopes distinct.

## Withdrawal failure and recovery

The earlier `0.0011 GEN` withdrawal on legacy Hub `0x49Cb64ba7CA953ffABE72eF34841067532FBFcF3` is not recoverable through that immutable contract: the legacy Hub shows zero credit, its child did not credit the EOA, and it has no callable authenticated recovery method. Whether protocol operators can recover the value is unknown. See [`deployments/legacy-withdrawal-failure.json`](../deployments/legacy-withdrawal-failure.json). This is separate from the current successful payout above.

On the current deployment, `withdraw()` serializes a recipient's pending outbound transfer. `reconcile_withdrawal` independently fetches the exact finalized parent/child pair through the fixed-method receipt gateway and only marks delivery after validating the recipient, amount, sender, parent link, finality, and `value_credited`. A verified failed child restores claimable credit and records a backing shortfall; later withdrawals are blocked until recapitalization restores solvency. No timeout-only re-credit is allowed. The delivered-child path is proven live. The failed-child recovery branch and invalid/unavailable receipt cases are covered deterministically but have not been induced on-chain on this release.

The gateway at `/api/payout-receipt` is read-only and accepts a transaction hash, returning a bounded receipt projection from StudioNet RPC. Validator consensus replays the gateway data; it is not a cryptographic inclusion proof and depends on both the gateway and RPC availability.

## HTTP failure handling and provenance limits

SourceWitness classifies temporary statuses including HTTP 429 and 503 as `UNAVAILABLE`; NoemaHub returns the researcher bond and marks that submission retryable rather than awarding the bond to the sponsor. Permanent missing-source responses such as 404 are rejected under policy. A document-looking response body cannot override a non-success HTTP status. These branches are covered by direct tests.

The records bind the requested URL, HTTP status, response-body digest, claim digest, and observation time. The runtime does not prove the final response origin, redirect chain, or publisher identity; these fields are intentionally not represented as authenticated provenance.

The published manifest parity vector is also covered by a test: dossier `noema-1`, evidence `base-1` and `note-1`, canonical manifest root `9f18409690f81c54c257d64c0e15572e7c77674afa5c7707de57e4411c87f000`.
