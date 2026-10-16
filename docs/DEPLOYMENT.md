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
| NoemaHub | `0x52282B21156C22d1800d0302Ea1e0FFc4De637BF` | `0x71b31cd3590206fc784df5e75a5ce2834713c1308290ae8cf17731ac3735dcc8` |
| SourceWitness | `0x48B78b602D42bdA41DdA4ABC11820E5CE34391f7` | `0xacee9ece5d481f55ddfbb559a48c9da7ba07125df8e743d3e6ad7879ff230431` |
| VerdictEngine | `0x272F7f1ab9edd2320c9C5F697E0DC1AA97795745` | `0x5ad818f422b8cbec8ca60ae86272ec9a02a99fc4577c03b2e5eb22e2d85d8d9e` |

The one-time worker binding transaction is `0x0528258d86d8e291227eb89176c9b32a02a0130443a469b73e91d4ba01546970`. This release enables native payouts and was deployed from commit `623407424e30e5b31daf842c82f3031ae34f8227`; `deployments/studionet.json` records source hashes independently matched against all three deployed contracts.

## Real-network acceptance test

Run the fresh-Hub acceptance harness while an unlocked StudioNet researcher account is active:

```bash
genlayer account use eventweaver
npm run e2e:studionet
```

The runner removes known stale generated bundles before the GenLayer CLI scans `deploy/`, verifies native account balances and transaction receipts through direct StudioNet JSON-RPC, supports resuming an interrupted run, and returns unused temporary sponsor funds to the researcher. By default, its generated sponsor key is saved with mode `0600` until the balance is swept or proven zero. For a user-provided throwaway key, set `NOEMA_E2E_SPONSOR_PRIVATE_KEY` in the process environment: the runner keeps that key in memory only and does not write it to disk or the evidence artifact. It rejects a sponsor account that is the same as the researcher account. Keep generated `.compiled.js` files out of source control and do not pass the harness as `--contract`.

For a deployment signer whose CLI keystore password is unavailable, the runner also accepts `NOEMA_E2E_DEPLOYER_PRIVATE_KEY`. Enter it through a hidden shell prompt, not a command-line argument. The Node runner removes it from its environment immediately, uses it only in process memory, requires at least `0.005 GEN` in that account, and never writes it to the deployment manifest or test artifact; the invoking shell should unset its own variable when the command returns.

The current acceptance dossier `noema-1` used first-party OpenAI Codex Git tree and LICENSE URLs. Its result was `POSITION_A`; `note-1` was the sole decisive submission and the counterfactual without it was `UNRESOLVED`. The researcher earned `0.0011 GEN`, including the returned bond. Withdrawal parent `0x05274e66eb4093cb16e48b1a7b8f3080bf92ff185a689ca91b67300456739120` emitted child `0xc97a20a6510b2597b37545acecc77f4e8de9334c54faa77cc07727f5f2be2661`, finalized with `value_credited=true`, and was reconciled by transaction `0x610f43f82eb842592891fa3554d2ff73f728d705de3bd3eb1e3ae2705ea5a829` as `DELIVERED`. Hub credit changed from `1100000000000000` to zero; the wallet changed from `999000000999876277587324887999999998992` to `999000000999876277587325987999999998992` atto. Accounting and solvency remained true, and a duplicate withdrawal was rejected. The temporary sponsor's unused `0.002 GEN` was returned separately and is not included in the payout delta.

The current transaction-level acceptance proof is [`deployments/studionet-e2e-latest.json`](../deployments/studionet-e2e-latest.json). It is a CLI/GenLayerJS-originated run, not a browser-wallet-originated run. A previous deployment had a failed withdrawal of `0.0011 GEN`; that old immutable Hub debited the credit and had no authenticated failure callback or re-credit method, so that specific credit is not recoverable through the contract. This fresh deployment is separate and demonstrates successful delivery.

## Production application checks

The frontend and backend API are deployed at [neoma-hub.vercel.app](https://neoma-hub.vercel.app); the last recorded Vercel production deployment ID is `dpl_9LNrBewxcNivepMiNLaqLJLQc1k1`. Its `/api/health` endpoint was checked after release and reported chain 61999, reachable RPC, and available Hub code. Home, Field list, dossier detail, real-data autofill, Method, and Vault were smoke-tested; the live dossier page read the deployed Hub and showed its settled evidence. These are release-time observations, not a claim that the endpoint was reachable during every later verification attempt.

The funded payout lifecycle recorded above ran through GenLayerJS with a throwaway signer; it was not a browser-wallet-originated payout. A separate browser-wallet run opened and funded `noema-2` with 10 GEN, completed the baseline source-attestation and unresolved-verdict callback path, and successfully sealed a researcher commitment. Its subsequent `disclose` transaction finalized with a GenVM error (`disclosure does not match its seal`) and rolled back; the production dossier readback remained `OPEN`, with one evidence record and zero disclosures. All seven browser transaction receipts and the state readback are recorded in [`deployments/studionet-browser-wallet-verification.json`](../deployments/studionet-browser-wallet-verification.json). This is not a successful browser disclosure or payout test. The frontend verifies execution outcomes, child receipts, wallet balance deltas, and authoritative Hub state. Permissionless `reconcile_withdrawal` independently re-fetches finalized parent and child records in validators, restores a claim to `FAILED_RECREDITED` only for a verified failed child, records any backing shortfall, and blocks another withdrawal until recapitalization. There is no timeout-based re-credit. The fixed-method `/api/payout-receipt` GET endpoint adapts StudioNet's public RPC POST method for GenVM web access; it accepts only a 32-byte transaction hash and returns an allowlisted read-only projection. Receipt validation remains dependent on the Vercel gateway and StudioNet RPC and is consensus-replayed evidence, not a cryptographic inclusion proof.
