# Deployment

## Secure bootstrap

Noema's circular authentication requirement is resolved without mutable administration:

1. deploy `NoemaHub` with empty worker addresses;
2. deploy `SourceWitness` with the Hub address;
3. deploy `VerdictEngine` with the Hub address;
4. call `NoemaHub.configure` once;
5. the Hub clears its bootstrapper and permanently rejects reconfiguration.

The deployment script refuses any chain other than StudioNet `61999`.

```bash
npm install
genlayer network set studionet
genlayer network info
genlayer deploy
```

The deployment manifest is written to `deployments/studionet.json`; frontend local settings are updated to the resulting contract addresses. The deploy script validates finalized GenVM execution receipts and reads every deployed contract's source through `getContractCode`, requiring an exact SHA-256 match before writing the manifest.

## Current production release

The current StudioNet deployment is:

| Contract | Address | Deployment transaction |
|---|---|---|
| NoemaHub | `0x2abC9A485924F7fB43C31875ff6bc865a1827633` | `0xd92c8442029bf535f1e249c546f4c2086c9321744c0a136694568491cae78ca3` |
| SourceWitness | `0x33Ae4Aa4D03AA732f67ea83d57580e91D0D2f12C` | `0xd2ea92dd2a45bb54ea32e725019bec455c3b110e6325517c3be4cdb247ae29b2` |
| VerdictEngine | `0xf4917237F5e4e6b990BD6B982B53b8d04f244439` | `0x7f9fccce509e8c1d0ea95fade4c0e09390c71344801d2bb198c1cfe8375331d4` |

The one-time worker binding transaction is `0x5f1c06fd215f4bcc5840501810d91a743e96b2a3427b313716043fb20eae6add`. This release enables native payouts and identifies its uncommitted deployment snapshot as `WORKTREE-2026-10-20-v4`; `deployments/studionet.json` records exact local and independently retrieved deployed source SHA-256 values for all three contracts.

## Real-network acceptance test

Run the fresh-Hub acceptance harness while an unlocked StudioNet researcher account is active:

```bash
genlayer account use eventweaver
npm run e2e:studionet
```

The runner removes known stale generated bundles before the GenLayer CLI scans `deploy/`, verifies native account balances and transaction receipts through direct StudioNet JSON-RPC, supports resuming an interrupted run, and returns unused temporary sponsor funds to the researcher. By default, its generated sponsor key is saved with mode `0600` until the balance is swept or proven zero. For a user-provided throwaway key, set `NOEMA_E2E_SPONSOR_PRIVATE_KEY` in the process environment: the runner keeps that key in memory only and does not write it to disk or the evidence artifact. It rejects a sponsor account that is the same as the researcher account. Keep generated `.compiled.js` files out of source control and do not pass the harness as `--contract`.

For a deployment signer whose CLI keystore password is unavailable, the runner also accepts `NOEMA_E2E_DEPLOYER_PRIVATE_KEY`. Enter it through a hidden shell prompt, not a command-line argument. The Node runner removes it from its environment immediately, uses it only in process memory, requires at least `0.005 GEN` in that account, and never writes it to the deployment manifest or test artifact; the invoking shell should unset its own variable when the command returns.

The current acceptance dossier `noema-1` used immutable first-party OpenAI Codex Git tree and LICENSE objects. Its result was `POSITION_A`; `note-1` was the sole decisive submission and the counterfactual without it was `UNRESOLVED`. The full 10,926-byte LICENSE response was digested and the claim was bound to the exact support quote `Licensed under the Apache License, Version 2.0 (the "License");`. The researcher earned `0.0011 GEN`, including the returned bond. Withdrawal parent `0x960e79ee4f3d8a94ab027c225f63a7f8a811533fd38ac63601ef12c568ff66b1` emitted child `0x5fe23177c3f83609c8f8921979a26a41ff4dd3b846f1feb6f6cffb79d0e27fc8`, finalized with `value_credited=true`, and was reconciled by `0xf3f5207418601c216e9356c68a95e7fbb3265786133fb2fb3fcedb0e41476c1f` as `DELIVERED`. Hub credit changed from `1100000000000000` to zero; the wallet changed from `10020999999999999997` to `10022099999999999997` atto. Accounting and solvency remained true, and a duplicate withdrawal was rejected. The temporary sponsor's unused `0.002 GEN` was returned separately and its generated key file was removed.

The current transaction-level acceptance proof is [`deployments/studionet-e2e-latest.json`](../deployments/studionet-e2e-latest.json). It is a CLI/GenLayerJS-originated run and demonstrates successful delivery on the current contracts. Historical legacy-contract incidents are kept separately in [`deployments/legacy-withdrawal-failure.json`](../deployments/legacy-withdrawal-failure.json) and are not evidence about this release.

## Production application checks

The hardened frontend is deployed at [neoma-hub.vercel.app](https://neoma-hub.vercel.app) as Vercel production deployment `dpl_7cY56FXJ5UQeHrcP8zE94BfbZzy2`. Its 2026-10-20 `/api/health` response reported chain 61999, Hub `0x2abC9A485924F7fB43C31875ff6bc865a1827633`, reachable RPC, and available Hub code. The production dossier page visibly renders the frozen rules root, final manifest root, exact support quote, full source byte count, verified content-addressed origin, decisive record, and final resolution.

The funded payout lifecycle recorded above ran through GenLayerJS with a throwaway signer. The separate production browser-wallet run funded dossier `noema-2` from `0x7401c129EDfc26E68FE19309fE461eb3Db1058Eb`; its source request received HTTP 403, so the asynchronous SourceWitness callback rejected it, the Hub recorded no evidence, closed the dossier, and atomically restored the full `0.001 GEN` as sponsor credit. This is a verified browser-wallet failure/rollback lifecycle, not a browser-originated payout claim. In the hardened source, permissionless `reconcile_withdrawal` re-fetches finalized parent and child records directly from canonical StudioNet RPC under validator replay, changes a verified failed child to `FAILED_RECREDITED` exactly once, consumes each receipt pair once, records any backing shortfall, and blocks another withdrawal until recapitalization. The project-controlled Vercel route is not a settlement authority.
