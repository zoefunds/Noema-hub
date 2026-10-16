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
| NoemaHub | `0xB62714FDc8B0240360616Cb24e69D2B819Cda0F8` | `0xda1375a3fdf912bd0316ef16a6a947c3445b9b225cde41e81f13082f731b6174` |
| SourceWitness | `0x1413B9687045b539e74AEE323b119a7B19dCBBF6` | `0xa7f5638a77a80ce3c21351625086c6b1f95dee0d0ce1704000007ba0d9e58155` |
| VerdictEngine | `0x2406AE364F5c58f5069418CfF71c00faBb82F67A` | `0xa445a2575a5654b02bcf1a4b9de3a7198894b6ed97804746a3e5e9d9a1208cc2` |

The one-time worker binding transaction is `0xf5e676e5a3e44a80e96244fafc00a7b7875960cfbce99addf7047bc6b473640d`. The release enables native payouts. The full deployed-source digests, exact reviewed source commit (`835353960b9568327cc34ffc28a74713392c8d24`), deployment hashes, and verification status are in `deployments/studionet.json`.

## Real-network acceptance test

Run the fresh-Hub acceptance harness while an unlocked StudioNet researcher account is active:

```bash
genlayer account use eventweaver
npm run e2e:studionet
```

The runner removes known stale generated bundles before the GenLayer CLI scans `deploy/`, verifies native account balances and transaction receipts through direct StudioNet JSON-RPC, supports resuming an interrupted run, and returns unused temporary sponsor funds to the researcher. By default, its generated sponsor key is saved with mode `0600` until the balance is swept or proven zero. For a user-provided throwaway key, set `NOEMA_E2E_SPONSOR_PRIVATE_KEY` in the process environment: the runner keeps that key in memory only and does not write it to disk or the evidence artifact. It rejects a sponsor account that is the same as the researcher account. Keep generated `.compiled.js` files out of source control and do not pass the harness as `--contract`.

For a deployment signer whose CLI keystore password is unavailable, the runner also accepts `NOEMA_E2E_DEPLOYER_PRIVATE_KEY`. Enter it through a hidden shell prompt, not a command-line argument. The Node runner removes it from its environment immediately, uses it only in process memory, requires at least `0.005 GEN` in that account, and never writes it to the deployment manifest or test artifact; the invoking shell should unset its own variable when the command returns.

The current acceptance dossier `noema-4` used official first-party OpenAI Codex Git tree and LICENSE URLs. Its result was `POSITION_A`; `note-2` was the only decisive submission and the counterfactual without it was `UNRESOLVED`. The researcher earned `0.0011 GEN`, including the returned bond. Withdrawal parent `0x48ec8f06a14e0b8a5c76124f4b7b4817e8907245b2201249c3eaded1ef50067b` emitted child `0x95cf5c004ee9db89314f20cfad4d5d90af453b743b3ec033f77e993ac60999ee`, finalized with `value_credited=true`, and sent exactly `1100000000000000` atto. Hub credit changed from `1100000000000000` to zero; the wallet changed from `10023199999999999997` to `10024299999999999997` atto; accounting remained true. A duplicate attempt finalized with GenVM `ERROR`, `value_credited=false`, and no second payout child. The temporary sponsor's remaining `0.002 GEN` was returned separately and is not included in the payout delta.

The full transaction-level record is in `deployments/e2e-studionet.json`. A previous deployment had a failed withdrawal of `0.0011 GEN`; that old immutable Hub debited the credit and had no authenticated failure callback or re-credit method, so that specific credit is not recoverable through the contract. This fresh deployment is separate and demonstrates successful delivery.

## Production application checks

The frontend and backend API are deployed at [neoma-hub.vercel.app](https://neoma-hub.vercel.app), production deployment `dpl_EPUKWxuCnxaMQgA6FNYRgXkr7PAz`. Its `/api/health` endpoint reports the current Hub, chain 61999, reachable RPC, and available Hub code. After deployment, Home, Field list, dossier detail, real-data autofill, Method, and Vault were checked in a browser; all principal routes returned HTTP 200.

The browser used for the previous live verification had no connected wallet. That lifecycle ran through GenLayerJS and is not described as browser-originated. The deployed release's frontend only verifies successful outgoing child receipts and recipient balance deltas; it cannot recover a failed child. The current source adds consensus-replayed receipt reconciliation, restores a claim into `FAILED_RECREDITED` only after a finalized failed child is confirmed, and blocks another withdrawal until any resulting backing shortfall is recapitalized. It deliberately has no timeout-based re-credit. This recovery implementation is not live until the immutable Hub and frontend are redeployed and the finalized failed-child path is verified on StudioNet. Receipt validation re-fetches public transaction records from the configured StudioNet RPC; it is consensus-compared but is not a cryptographic inclusion proof.
