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
| NoemaHub | `0xD3B1A426bFD37f69a968e8Db2168edBA4E5854B1` | `0x4a7c9fd25fde31a6762f00904c5bd99a40d417321c44044f85b75ae61f7ea09d` |
| SourceWitness | `0x4F124634366603a3d29F9114F6cC995E40b54bB3` | `0x0b2dcd0c860de815e0371e5bbba86d8a543281edff24f979b2349dece91c120a` |
| VerdictEngine | `0x7C2eC0d75b08fDF7e04A9C657A9DE6e2cB4FA65b` | `0x30d31ef770cffdea8548a58c2ecaa6285c529956e87d806577ffe2ee2e162be6` |

The one-time worker binding transaction is `0x44dac0043e87c0df6255056aaae305a8504bd41404fb16ff24b0bd40482774dc`. This release enables native payouts and its contract sources are committed in `ae10755e078b10acce19e30fb285d275efc57653` (the queue-delay fairness fix); `deployments/studionet.json` records exact local and independently retrieved deployed source SHA-256 values for all three contracts.

Previous releases are superseded and no longer bound to the production frontend: commit `396ec24b77f5e635df6a1cfb962f4ad128745420` (Hub `0xB300efF2985bFd06d01D014c8f9EFD502726D76C`), and before that commit `2391ac15d210e8d505cb7bd3c8e08d73788883b3` (Hub `0xcBcfF1dc3FD979fb48d65E078Ca7a8fcf98483e4`, SourceWitness `0x9D2CF136821F01369fbBc462F5fE868670c92785`, VerdictEngine `0x22C980402f1bF4D15333aF4CE5002A3f19DC9eA9`).

## Real-network acceptance test

Run the fresh-Hub acceptance harness while an unlocked StudioNet researcher account is active:

```bash
genlayer account use <unlocked-funded-account>
npm run e2e:studionet
```

The runner removes known stale generated bundles before the GenLayer CLI scans `deploy/`, verifies native account balances and transaction receipts through direct StudioNet JSON-RPC, supports resuming an interrupted run, and returns unused temporary sponsor funds to the researcher. By default, its generated sponsor key is saved with mode `0600` until the balance is swept or proven zero. For a user-provided throwaway key, set `NOEMA_E2E_SPONSOR_PRIVATE_KEY` in the process environment: the runner keeps that key in memory only and does not write it to disk or the evidence artifact. It rejects a sponsor account that is the same as the researcher account. Keep generated `.compiled.js` files out of source control and do not pass the harness as `--contract`.

For a deployment signer whose CLI keystore password is unavailable, the runner also accepts `NOEMA_E2E_DEPLOYER_PRIVATE_KEY`. Enter it through a hidden shell prompt, not a command-line argument. The Node runner removes it from its environment immediately, uses it only in process memory, requires at least `0.005 GEN` in that account, and never writes it to the deployment manifest or test artifact; the invoking shell should unset its own variable when the command returns.

The current acceptance dossier `noema-1` used immutable first-party OpenAI Codex Git tree and LICENSE objects. Its result was `POSITION_A`; `note-1` was the sole decisive submission and the counterfactual without it was `UNRESOLVED`. The full response was digested and the claim was bound to the exact support commitment recorded in `deployments/e2e-studionet.json`. The researcher earned `0.0011 GEN` (`1100000000000000` atto), including the returned bond. Current-release withdrawal parent `0x57e1fd61595da4e39c93656f7d8a62fabd681792619d87cccd9680f6e286dffe` emitted child `0xadec187d58ecc8d78a3e431766cd4e37d0749c5f32b792e104f05ca16da8c0ce` and was reconciled as `DELIVERED` via transaction `0xc25c69cf530b09a4e15f2da4e572c0e98c07b407bada28d499b092810225f7d5`. Hub credit changed to zero; the wallet increased from `999000000999876277586181587999999998992` to `999000000999876277586182687999999998992` atto, an exact `1100000000000000` atto delta. Accounting and solvency remained true before and after, and a duplicate reconciliation attempt against the same withdrawal was rejected.

The current transaction-level acceptance proof is [`deployments/e2e-studionet.json`](../deployments/e2e-studionet.json), specifically its `freshRedeploymentRun` record. It is a CLI/GenLayerJS-originated run and demonstrates successful delivery on the current contracts. Historical legacy-contract incidents are kept separately in [`deployments/legacy-withdrawal-failure.json`](../deployments/legacy-withdrawal-failure.json) and are not evidence about this release.

To reproduce the real deadline path without redeploying, activate a funded account and run:

```bash
NOEMA_TIMEOUT_E2E=1 genlayer deploy
```

The timeout harness resumes its exact pending dossier after transient RPC failures, refuses to replace the configured StudioNet release, records the emitted child transaction, and writes [`deployments/studionet-timeout-rollback.json`](../deployments/studionet-timeout-rollback.json). It waits for the contract's real 1,800-second deadline; it does not warp local time or shorten the deployed window.

For a deployment signer whose CLI keystore password is unavailable, [`run-timeout-e2e.mjs`](../run-timeout-e2e.mjs) runs the same harness directly against `deploy/timeoutRollback.ts` using a throwaway key supplied through `NOEMA_TIMEOUT_DEPLOYER_PRIVATE_KEY` (same pattern as `NOEMA_E2E_DEPLOYER_PRIVATE_KEY` for `run-studionet-e2e.mjs`): enter it through a hidden shell prompt, not a command-line argument. The script deletes it from its own environment immediately, keeps it in process memory only, and never writes it to the deployment manifest or test artifact.

```bash
NOEMA_TIMEOUT_DEPLOYER_PRIVATE_KEY=<hidden-prompt-value> node --import tsx run-timeout-e2e.mjs
```

## Production application checks

The hardened frontend is deployed at [neoma-hub.vercel.app](https://neoma-hub.vercel.app) as Vercel production deployment `dpl_BRL5K2Hqe53yDccYNTHCGKgn8J59`. Its 2026-10-21 `/api/health` response reported chain `61999`, Hub `0xD3B1A426bFD37f69a968e8Db2168edBA4E5854B1`, reachable RPC, and available Hub code. The `neoma-hub` Vercel project's `NEXT_PUBLIC_NOEMA_HUB_ADDRESS`, `NEXT_PUBLIC_NOEMA_WITNESS_ADDRESS`, and `NEXT_PUBLIC_NOEMA_ENGINE_ADDRESS` production environment variables were updated to this release before the deploy, and a browser check of the live site's homepage, dossier listing, `noema-1` detail page, dossier-creation form (including its autofill), protocol notes, and vault page confirmed each renders correctly against the new Hub. The production dossier page visibly renders the frozen rules root, final manifest root, exact support quotes for both evidence records, full source byte counts, and verified content-addressed origin for both the baseline and the decisive disclosure.

The funded payout lifecycle recorded above ran through GenLayerJS with a throwaway signer, in the same run that deployed these contracts (`run-studionet-e2e.mjs` with `NOEMA_FORCE_REDEPLOY=1`). The browser-wallet signing flows themselves (seal/reveal/withdraw via an injected wallet) were not driven through the production UI for this release — that requires a real wallet extension — but the frontend was confirmed to correctly read and render the exact on-chain state those flows produced. The earlier browser-wallet rollback artifact targets an immediately preceding release's contracts and is retained as historical evidence, not a claim about the current Hub; the current-release timeout acceptance run below, by contrast, is current-Hub evidence. In the hardened source, permissionless `reconcile_withdrawal` re-fetches finalized parent and child records directly from canonical StudioNet RPC under validator replay, changes a verified failed child to `FAILED_RECREDITED` exactly once, consumes each receipt pair once, records any backing shortfall, and blocks another withdrawal until recapitalization. The project-controlled Vercel route is not a settlement authority.

For the current-release timeout acceptance run, `noema-2` opening transaction `0xfe988dbb878a5c93d079e4012dffcd38408164bcd621f69eb49b159c47648baa` emitted asynchronous child `0x81847ec5d5bb95db07ad36763b142402b4e33a9095358ac5d80699c3ed50aee4`. After the actual 1,800-second deadline — reached via `run-timeout-e2e.mjs`, which resumed once from its own saved state after a transient StudioNet RPC failure mid-wait rather than opening a second dossier — `expire_stage` transaction `0x5d2df9e4c96acf1214c84aa8cd76e07605970f6bbc69660925908d2eb8f48824` closed the dossier with `BASELINE_STAGE_TIMEOUT` and restored exactly `0.001 GEN` to sponsor Hub credit while preserving accounting and solvency. An earlier, now-superseded release's timeout run is retained as historical evidence only.
