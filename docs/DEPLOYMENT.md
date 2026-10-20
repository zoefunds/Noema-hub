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
| NoemaHub | `0xcBcfF1dc3FD979fb48d65E078Ca7a8fcf98483e4` | `0x8fbb85ace3d58ec90b4eaaa1d89e3bae77699cbeb4fc8abba6d35c6cfb0d57ca` |
| SourceWitness | `0x9D2CF136821F01369fbBc462F5fE868670c92785` | `0xcae8b91b3d1d86a5e36ab649250055e4e55c05845e50295950ad1e5a8c20b40a` |
| VerdictEngine | `0x22C980402f1bF4D15333aF4CE5002A3f19DC9eA9` | `0x6a64467cbabe93f52479eafe977f0d5356f3f453d04e3135115352b5a6fbbb73` |

The one-time worker binding transaction is `0x61200c1f911a2be12ba93a48c5c1080bfac976b46904f64de182886d603ff532`. This release enables native payouts and its contract sources are committed in `2391ac15d210e8d505cb7bd3c8e08d73788883b3`; `deployments/studionet.json` records exact local and independently retrieved deployed source SHA-256 values for all three contracts.

## Real-network acceptance test

Run the fresh-Hub acceptance harness while an unlocked StudioNet researcher account is active:

```bash
genlayer account use <unlocked-funded-account>
npm run e2e:studionet
```

The runner removes known stale generated bundles before the GenLayer CLI scans `deploy/`, verifies native account balances and transaction receipts through direct StudioNet JSON-RPC, supports resuming an interrupted run, and returns unused temporary sponsor funds to the researcher. By default, its generated sponsor key is saved with mode `0600` until the balance is swept or proven zero. For a user-provided throwaway key, set `NOEMA_E2E_SPONSOR_PRIVATE_KEY` in the process environment: the runner keeps that key in memory only and does not write it to disk or the evidence artifact. It rejects a sponsor account that is the same as the researcher account. Keep generated `.compiled.js` files out of source control and do not pass the harness as `--contract`.

For a deployment signer whose CLI keystore password is unavailable, the runner also accepts `NOEMA_E2E_DEPLOYER_PRIVATE_KEY`. Enter it through a hidden shell prompt, not a command-line argument. The Node runner removes it from its environment immediately, uses it only in process memory, requires at least `0.005 GEN` in that account, and never writes it to the deployment manifest or test artifact; the invoking shell should unset its own variable when the command returns.

The current acceptance dossier `noema-1` used immutable first-party OpenAI Codex Git tree and LICENSE objects. Its result was `POSITION_A`; `note-1` was the sole decisive submission and the counterfactual without it was `UNRESOLVED`. The full 10,926-byte LICENSE response was digested and the claim was bound to the exact support quote `Licensed under the Apache License, Version 2.0 (the "License");`. The researcher earned `0.0011 GEN`, including the returned bond. Withdrawal parent `0x0aa20b30de1ee715cfb510b610ce1e7006f9b7a44a6abb7920f0f070738e6550` emitted child `0x68f5b61a30dc46d14d61bf6f6bcbbbc49bfebb94288a7fe9379c27263495ad4f`, finalized with `value_credited=true`, and was reconciled by `0x6c953a16ec5769e95025eeab1f8b35c07cb61708a38e89748f5adbb549a5aa06` as `DELIVERED`. Hub credit changed from `1100000000000000` to zero; the wallet changed from `459599999967045000` to `460699999967045000` atto. Accounting and solvency remained true, and a duplicate withdrawal was rejected. The temporary sponsor's unused `0.002 GEN` was returned separately and its generated key file was removed.

The current transaction-level acceptance proof is [`deployments/e2e-studionet.json`](../deployments/e2e-studionet.json), specifically its `freshRedeploymentRun` record. It is a CLI/GenLayerJS-originated run and demonstrates successful delivery on the current contracts. Historical legacy-contract incidents are kept separately in [`deployments/legacy-withdrawal-failure.json`](../deployments/legacy-withdrawal-failure.json) and are not evidence about this release.

To reproduce the real deadline path without redeploying, activate a funded account and run:

```bash
NOEMA_TIMEOUT_E2E=1 genlayer deploy
```

The timeout harness resumes its exact pending dossier after transient RPC failures, refuses to replace the configured StudioNet release, records the emitted child transaction, and writes [`deployments/studionet-timeout-rollback.json`](../deployments/studionet-timeout-rollback.json). It waits for the contract's real 1,800-second deadline; it does not warp local time or shorten the deployed window.

## Production application checks

The hardened frontend is deployed at [neoma-hub.vercel.app](https://neoma-hub.vercel.app) as Vercel production deployment `dpl_DpyU9D9GUUrGifdvdp2ciN3hcbQz`. Its 2026-10-20 `/api/health` response reported chain 61999, Hub `0xcBcfF1dc3FD979fb48d65E078Ca7a8fcf98483e4`, reachable RPC, and available Hub code. The production dossier page visibly renders the frozen rules root, final manifest root, exact support quote, full source byte count, verified content-addressed origin, decisive record, and final resolution.

The funded payout lifecycle recorded above ran through GenLayerJS with a throwaway signer. The earlier browser-wallet rollback artifact targets the immediately preceding source-matched release and is retained as historical evidence, not represented as a transaction on the current Hub. The current release adds a live asynchronous StudioNet timeout record in `deployments/studionet-timeout-rollback.json`. In the hardened source, permissionless `reconcile_withdrawal` re-fetches finalized parent and child records directly from canonical StudioNet RPC under validator replay, changes a verified failed child to `FAILED_RECREDITED` exactly once, consumes each receipt pair once, records any backing shortfall, and blocks another withdrawal until recapitalization. The project-controlled Vercel route is not a settlement authority.

For the timeout acceptance run, `noema-2` opening transaction `0x662aaeef90ae808f70e29205752f51b44b2c3d3840d84be5949851d4a506f010` emitted asynchronous child `0x1ffc205596a9d8d8bcde797ce948bd64aefa8a7225171f506e5a5ecd1581a072`. After the actual 1,800-second deadline, `expire_stage` transaction `0x0498f234793d69aa30db3d09a7f71d3014ee585fa4a9a314b0e39f5f73b7c6aa` closed the dossier with `BASELINE_STAGE_TIMEOUT` and restored exactly `0.001 GEN` to sponsor Hub credit while preserving accounting and solvency.
