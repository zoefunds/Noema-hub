# Verification record

This document separates deterministic checks from public-network evidence. A transaction counts as a successful payout only when its finalized execution result, child transfer, wallet balance delta, and authoritative Hub state all agree.

## Reproduce the local checks

Run from the repository root with Python 3.12+ and Node.js 20+:

```bash
python -m pip install -r requirements.txt
npm install
npm run ci
```

The latest verified local run passed 52 direct contract tests, 4 sponsor-key safety tests, and 13 frontend tests. Frontend TypeScript checking and optimized production build also passed. Coverage includes complete-body inspection beyond the former 24,000-character boundary, fail-closed origin and redirect handling, verbatim support binding, frozen rules, FIFO callback enforcement, executable conflicting-evidence consensus with economically non-decisive settlement, stateful verdict-timeout rollback, direct canonical-RPC payout verification, forged/mismatched receipts, and stateful failed-receipt replay and duplicate-credit rejection.

The GitHub Actions workflow is `.github/workflows/quality.yml`. On 2026-10-20 the account billing page identified a failed payment authorization. Retrying the existing authorization failed again and GitHub instructed the owner to contact the bank or update the payment method. The fresh release-evidence run [`39456409579`](https://github.com/zoefunds/Noema-hub/actions/runs/39456409579) created both expected jobs but GitHub terminated each with zero executed steps. Until that owner-controlled billing action succeeds, no hosted green result is claimed. The complete workflow-equivalent command passes locally.

## Source-matched StudioNet deployment

The production manifest is [`deployments/studionet.json`](../deployments/studionet.json). The deployment script retrieved each contract's source independently with GenLayerJS `getContractCode` and required exact SHA-256 equality before writing the manifest:

The exact matching contract sources are committed in `aea785e7460e61e4739bd0fa2621af56b9d9c612`.

| Contract | Address | Deployed source SHA-256 | Match |
|---|---|---|---|
| NoemaHub | `0x8bEd4aB285B33CAefFEc06Fa175B797b58f531A5` | `b0fbc87430b507afeae95131bd9e8c920a603ead1395823ec2ed61d28c55a219` | yes |
| SourceWitness | `0x97F7625A26C9419FA4e6cb2ec44bf7f740BA643c` | `d1d115b6e79e450689fcf7391a56ce1165105c45391d01f31f07539b56aacd44` | yes |
| VerdictEngine | `0xFB07B39bbBa8410ca2df209D09632654e66C89ec` | `e344a760ab68c10c24dd849de6c12c5974ea60afaeb157a1b9a4bf39ccfddc75` | yes |

Deployment transactions are `0xdee8bc0903079cc4d95ed949012c710e9b2ff030bb31cea4a7eae5f2f6636ca4`, `0x0718ac3812fbf5cfe39610e1a10082c18996c24db74f074d5456ca9edc933917`, and `0xa94e5424b21c08c3808a96a7f6b4403169ee7b883e63e45a38d3d96a03aee9ff`; the one-time Hub binding transaction is `0x64ada52b21b3dfaaeca73e61bebe42164fb6e4171c6ff14c204a69b0ac231804`.

## Real StudioNet research and payout run

The concise record documents a completed CLI/GenLayerJS run against the deployed Hub, using official OpenAI Codex public sources:

- dossier `noema-1` asks whether the default-branch root `LICENSE` expressly declares Apache License 2.0;
- baseline Git tree request: immutable tree `b8be7cdf257c4f6aaf4250060a5b37d5c045ab5d`, HTTP 200, all 9,508 response bytes digested as `8b5c5e45ef85336331f27ca970ae611386237bac81d1fbc6a10ac998df64f75e`;
- decisive source: immutable commit `e1b9c9457ceca75a99b034a5df39ac48c3998d15` root `LICENSE`, HTTP 200, all 10,926 bytes digested as `d17f227e4df5da1600391338865ce0f3055211760a36688f816941d58232d8dc`, with exact support quote digest `55f12528ddd4240e797f6391c80f5cf883e9c281253ad296c30b97dd4810c0a6`;
- outcome `POSITION_A`, decisive evidence `note-1`, and counterfactual without `note-1` `UNRESOLVED`; frozen rules root `0fb227e6ea0e9acf6fd01411df467621cacdd7a5fe96314a61eef9cedf3c23dc`; manifest root `1dd2c430496e9bd5b99ca4b41b34a0f927af12b5c20e1d9d2edfe7d5dff5133e`;
- sponsor funding `0x1a3715086cceba772e08a39079aa4034571ff1d53f741eba255ea84554c866b8`; dossier opening `0xb5e3ea3142c926a9f6b35c8dbb5996a0ac8de11cb37dae2a6580591930efecb3`; commitment seal `0x06ef3ed97f0c339d93b7596866459248a3837a564a0157249684c2aea8e2a481`; disclosure `0x0d76d14dc4192e0a2b7af5e19388fd8b4177da9d5f5826c822e5d7ec2a01ca54`;
- reward plus returned bond credited to the researcher: `1100000000000000` atto GEN (`0.0011 GEN`);
- withdrawal parent `0x0aa20b30de1ee715cfb510b610ce1e7006f9b7a44a6abb7920f0f070738e6550`; finalized child `0x68f5b61a30dc46d14d61bf6f6bcbbbc49bfebb94288a7fe9379c27263495ad4f`, recipient `0x1c2e587043568239B2fcaeC5f96F278EB134b7f5`, exact value `1100000000000000` atto GEN, `value_credited=true`;
- recipient balance moved from `459599999967045000` to `460699999967045000` atto GEN, an exact increase of `1100000000000000`;
- reconciliation `0x6c953a16ec5769e95025eeab1f8b35c07cb61708a38e89748f5adbb549a5aa06` read back `DELIVERED` with the exact parent and child IDs; Hub credit moved from `1100000000000000` to `0`; accounting and solvency remained true; duplicate withdrawal was rejected;
- a separate finalized transaction returned the temporary sponsor's unused `0.002 GEN`; it is not part of the recipient's payout delta.

The successful research-and-payout run above was initiated with GenLayerJS. [`deployments/studionet-browser-wallet-verification.json`](../deployments/studionet-browser-wallet-verification.json) is explicitly marked `SUPERSEDED` and retained only as historical browser-wallet rollback evidence from the preceding deployment; none of its addresses or transactions are current-release evidence. The current release's asynchronous timeout and refund evidence is [`deployments/studionet-timeout-rollback.json`](../deployments/studionet-timeout-rollback.json).

The current Hub's timeout dossier `noema-2` was funded with `0.001 GEN` by finalized parent `0x662aaeef90ae808f70e29205752f51b44b2c3d3840d84be5949851d4a506f010`, which emitted asynchronous SourceWitness child `0x1ffc205596a9d8d8bcde797ce948bd64aefa8a7225171f506e5a5ecd1581a072`. Conflicting dynamic UUID observations prevented that child from completing consensus, leaving the Hub in `BASELINE_WITNESSING` through its real 1,800-second stage deadline. Permissionless `expire_stage` finalized as `0x0498f234793d69aa30db3d09a7f71d3014ee585fa4a9a314b0e39f5f73b7c6aa`; authoritative readback then showed `CLOSED_REFUNDED`, `BASELINE_STAGE_TIMEOUT`, an empty pending id, reward escrow zero, sponsor credit increasing exactly from `0` to `1000000000000000`, and both accounting and solvency true.

## Historical legacy withdrawal incident

The earlier `0.0011 GEN` withdrawal on legacy Hub `0x49Cb64ba7CA953ffABE72eF34841067532FBFcF3` is not recoverable through that immutable contract: the legacy Hub shows zero credit, its child did not credit the EOA, and it has no callable authenticated recovery method. Whether protocol operators can recover the value is unknown. See [`deployments/legacy-withdrawal-failure.json`](../deployments/legacy-withdrawal-failure.json). This is separate from the current successful payout above.

In the hardened source, `withdraw()` serializes a recipient's pending outbound transfer. `reconcile_withdrawal` independently fetches the exact finalized parent/child pair directly from canonical StudioNet RPC under validator replay and only marks delivery after validating recipient, amount, sender, parent link, finality, `value_credited`, timestamp, calldata, and single-use receipt consumption. A verified failed child restores claimable credit once and records any backing shortfall; later withdrawals remain blocked until recapitalization restores solvency. No timeout-only re-credit is allowed.

The frontend `/api/payout-receipt` projection is no longer a settlement authority. The contract does not call it; settlement and recrediting use canonical StudioNet RPC directly.

## HTTP failure handling and provenance authentication

SourceWitness classifies temporary statuses including HTTP 429 and 503 as `UNAVAILABLE`; NoemaHub returns the researcher bond and marks that submission retryable rather than awarding the bond to the sponsor. Permanent missing-source responses such as 404 are rejected under policy. A document-looking response body cannot override a non-success HTTP status. These branches are covered by direct tests.

The records bind the requested URL and origin, verified response origin, HTTP status, complete response-body digest and size, exact support quote and digest, claim digest, and observation time. Ordinary redirects, origin changes, ambiguous repository identities, unsupported publisher/canonical claims, oversized sources, and unverifiable provenance fail closed. An explicitly allowlisted immutable GitHub raw/API pair may use the content-addressed fallback; it is labeled `VERIFIED_CONTENT_ADDRESSED_ORIGIN`, never promoted to a direct-response or publisher assertion, and still requires exact repository, immutable object, full-body, and support binding.

The live manifest root for dossier `noema-1`, evidence `base-1` and `note-1`, is `1dd2c430496e9bd5b99ca4b41b34a0f927af12b5c20e1d9d2edfe7d5dff5133e`.
