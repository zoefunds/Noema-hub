# Verification record

This document separates deterministic checks from public-network evidence. A transaction counts as a successful payout only when its finalized execution result, child transfer, wallet balance delta, and authoritative Hub state all agree.

## Reproduce the local checks

Run from the repository root with Python 3.12+ and Node.js 20+:

```bash
python -m pip install -r requirements.txt
npm install
npm run ci
```

The latest verified local run passed 48 direct contract tests, 4 sponsor-key safety tests, and 13 frontend tests. Frontend TypeScript checking and optimized production build also passed. Coverage includes complete-body inspection beyond the former 24,000-character boundary, fail-closed origin and redirect handling, verbatim support binding, frozen rules, FIFO callback enforcement, conflicting-evidence instructions, timeout rollback, direct canonical-RPC payout verification, forged/mismatched receipts, single-use receipt pairs, duplicate-credit prevention, and exact parent/child delivery matching.

The GitHub Actions workflow is `.github/workflows/quality.yml`. As of 2026-10-20, GitHub refuses to start hosted jobs because the repository account is locked for a billing issue; no hosted green result is claimed. The complete workflow-equivalent command passes locally. A hosted green run requires the repository owner to resolve that account-level lock and rerun the workflow.

## Source-matched StudioNet deployment

The production manifest is [`deployments/studionet.json`](../deployments/studionet.json). The deployment script retrieved each contract's source independently with GenLayerJS `getContractCode` and required exact SHA-256 equality before writing the manifest:

The exact matching contract sources are committed in `588ae6f2e25c1afcd2b80115cb57f00990b04e44`.

| Contract | Address | Deployed source SHA-256 | Match |
|---|---|---|---|
| NoemaHub | `0x2abC9A485924F7fB43C31875ff6bc865a1827633` | `eea25cd3a88acfe4a343665bff0451213e1a58084d6094669f7dd7c587f75813` | yes |
| SourceWitness | `0x33Ae4Aa4D03AA732f67ea83d57580e91D0D2f12C` | `d1d115b6e79e450689fcf7391a56ce1165105c45391d01f31f07539b56aacd44` | yes |
| VerdictEngine | `0xf4917237F5e4e6b990BD6B982B53b8d04f244439` | `e344a760ab68c10c24dd849de6c12c5974ea60afaeb157a1b9a4bf39ccfddc75` | yes |

Deployment transactions are `0xd92c8442029bf535f1e249c546f4c2086c9321744c0a136694568491cae78ca3`, `0xd2ea92dd2a45bb54ea32e725019bec455c3b110e6325517c3be4cdb247ae29b2`, and `0x7f9fccce509e8c1d0ea95fade4c0e09390c71344801d2bb198c1cfe8375331d4`; the one-time Hub binding transaction is `0x5f1c06fd215f4bcc5840501810d91a743e96b2a3427b313716043fb20eae6add`.

## Real StudioNet research and payout run

The concise record documents a completed CLI/GenLayerJS run against the deployed Hub, using official OpenAI Codex public sources:

- dossier `noema-1` asks whether the default-branch root `LICENSE` expressly declares Apache License 2.0;
- baseline Git tree request: immutable tree `b8be7cdf257c4f6aaf4250060a5b37d5c045ab5d`, HTTP 200, all 9,508 response bytes digested as `8b5c5e45ef85336331f27ca970ae611386237bac81d1fbc6a10ac998df64f75e`;
- decisive source: immutable commit `e1b9c9457ceca75a99b034a5df39ac48c3998d15` root `LICENSE`, HTTP 200, all 10,926 bytes digested as `d17f227e4df5da1600391338865ce0f3055211760a36688f816941d58232d8dc`, with exact support quote digest `55f12528ddd4240e797f6391c80f5cf883e9c281253ad296c30b97dd4810c0a6`;
- outcome `POSITION_A`, decisive evidence `note-1`, and counterfactual without `note-1` `UNRESOLVED`; frozen rules root `df394367db26b0679e0264119ae19ee7fdc0e251993ade4d8f8cd74f698184df`; manifest root `2296e3032f17dd20345a721179603d11d0b9aa3d57dfcbccfc59e693276ef27f`;
- sponsor funding `0x94ba50c1ec4afdb4d90163338ad54f2b5084229b4c7406f9ea1bfc10d8f061d6`; dossier opening `0x9872db46199da0e2fbedb3549100e404fe75f52dc92717e5c97a71e6ecdc25d5`; commitment seal `0x2213b59d32098b53c09c779c3203e702d971b08375ca9213e69804c7e02b3373`; disclosure `0x097492dd4f547e2b7ac811a91b1d76a8284bfbc41181aee49ed1435e1d36b011`;
- reward plus returned bond credited to the researcher: `1100000000000000` atto GEN (`0.0011 GEN`);
- withdrawal parent `0x960e79ee4f3d8a94ab027c225f63a7f8a811533fd38ac63601ef12c568ff66b1`; finalized child `0x5fe23177c3f83609c8f8921979a26a41ff4dd3b846f1feb6f6cffb79d0e27fc8`, recipient `0x7452084E1Cf767bf19C743051cFf27D9F7A87a4D`, exact value `1100000000000000` atto GEN, `value_credited=true`;
- recipient balance moved from `10020999999999999997` to `10022099999999999997` atto GEN, an exact increase of `1100000000000000`;
- reconciliation `0xf3f5207418601c216e9356c68a95e7fbb3265786133fb2fb3fcedb0e41476c1f` read back `DELIVERED` with the exact parent and child IDs; Hub credit moved from `1100000000000000` to `0`; accounting and solvency remained true; duplicate withdrawal was rejected;
- a separate finalized transaction returned the temporary sponsor's unused `0.002 GEN`; it is not part of the recipient's payout delta.

The successful research-and-payout run above was initiated with GenLayerJS. A separate production browser-wallet run is recorded in [`deployments/studionet-browser-wallet-verification.json`](../deployments/studionet-browser-wallet-verification.json). Wallet `0x7401c129EDfc26E68FE19309fE461eb3Db1058Eb` funded `0.001 GEN` in finalized `open_dossier` transaction `0x3ed8a768398edfa07f41c18ee7581d582a3eaa387bc89d5d62ce7537054de7b9`. The Hub asynchronously called the deployed SourceWitness in finalized transaction `0x74701345ea1398d2429fef957bfe5fca8b71cb14eab96c8e901f744cf48d0d48`; finalized callback `0x69f839ab2f90f28a56a0d2ffae8e4b689c197e6800dde3e78d72fa6e6e942d9d` returned `REJECTED` because the source request received HTTP 403. The attestation explicitly recorded `claim_supported=false`, `policy_compliant=false`, an empty support quote, and the basis `HTTP status 403 is outside the accepted 2xx range; classified as REJECTED.`

The authoritative Hub readback then showed `CLOSED_REFUNDED`, resolution `INVALID_OR_UNAVAILABLE_BASELINE`, zero evidence records, zero remaining dossier reward, and the complete `1000000000000000` atto GEN in the sponsor's Hub credit. This proves a real browser-originated funded transaction, asynchronous Hub→Witness→Hub execution, fail-closed handling, and atomic rollback. It intentionally does not claim a browser-originated research payout; the separate CLI payout record is the end-to-end reward-to-EOA proof.

## Historical legacy withdrawal incident

The earlier `0.0011 GEN` withdrawal on legacy Hub `0x49Cb64ba7CA953ffABE72eF34841067532FBFcF3` is not recoverable through that immutable contract: the legacy Hub shows zero credit, its child did not credit the EOA, and it has no callable authenticated recovery method. Whether protocol operators can recover the value is unknown. See [`deployments/legacy-withdrawal-failure.json`](../deployments/legacy-withdrawal-failure.json). This is separate from the current successful payout above.

In the hardened source, `withdraw()` serializes a recipient's pending outbound transfer. `reconcile_withdrawal` independently fetches the exact finalized parent/child pair directly from canonical StudioNet RPC under validator replay and only marks delivery after validating recipient, amount, sender, parent link, finality, `value_credited`, timestamp, calldata, and single-use receipt consumption. A verified failed child restores claimable credit once and records any backing shortfall; later withdrawals remain blocked until recapitalization restores solvency. No timeout-only re-credit is allowed.

The frontend `/api/payout-receipt` projection is no longer a settlement authority. The contract does not call it; settlement and recrediting use canonical StudioNet RPC directly.

## HTTP failure handling and provenance authentication

SourceWitness classifies temporary statuses including HTTP 429 and 503 as `UNAVAILABLE`; NoemaHub returns the researcher bond and marks that submission retryable rather than awarding the bond to the sponsor. Permanent missing-source responses such as 404 are rejected under policy. A document-looking response body cannot override a non-success HTTP status. These branches are covered by direct tests.

The records bind the requested URL and origin, verified response origin, HTTP status, complete response-body digest and size, exact support quote and digest, claim digest, and observation time. Ordinary redirects, origin changes, ambiguous repository identities, unsupported publisher/canonical claims, oversized sources, and unverifiable provenance fail closed. An explicitly allowlisted immutable GitHub raw/API pair may use the content-addressed fallback; it is labeled `VERIFIED_CONTENT_ADDRESSED_ORIGIN`, never promoted to a direct-response or publisher assertion, and still requires exact repository, immutable object, full-body, and support binding.

The live manifest root for dossier `noema-1`, evidence `base-1` and `note-1`, is `2296e3032f17dd20345a721179603d11d0b9aa3d57dfcbccfc59e693276ef27f`.
