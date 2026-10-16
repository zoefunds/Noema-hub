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

The runner removes known stale generated bundles before the GenLayer CLI scans `deploy/`, records a temporary sponsor key with mode `0600` before funding, verifies native account balances and transaction receipts through direct StudioNet JSON-RPC, supports resuming an interrupted run, and returns unused temporary sponsor funds to the researcher. Keep generated `.compiled.js` files out of source control and do not pass the harness as `--contract`.

The current acceptance dossier `noema-1` used official first-party OpenAI Codex Git tree and LICENSE URLs. Its result was `POSITION_A`; `note-1` was the only decisive submission and the counterfactual without it was `UNRESOLVED`. The researcher earned `0.0011 GEN`, including the returned bond. Withdrawal parent `0x48ec8f06a14e0b8a5c76124f4b7b4817e8907245b2201249c3eaded1ef50067b` emitted child `0x95cf5c004ee9db89314f20cfad4d5d90af453b743b3ec033f77e993ac60999ee`, finalized with `value_credited=true`, and sent exactly `1100000000000000` atto. Hub credit changed from `1100000000000000` to zero; the wallet changed from `10023199999999999997` to `10024299999999999997` atto; accounting remained true. A duplicate attempt finalized with GenVM `ERROR`, `value_credited=false`, and no second payout child. The temporary sponsor's remaining `0.002 GEN` was returned separately and is not included in the payout delta.

The full transaction-level record is in `deployments/e2e-studionet.json`. A previous deployment had a failed withdrawal of `0.0011 GEN`; that old immutable Hub debited the credit and had no authenticated failure callback or re-credit method, so that specific credit is not recoverable through the contract. This fresh deployment is separate and demonstrates successful delivery.

## Production application checks

The frontend and backend API are deployed at [neoma-hub.vercel.app](https://neoma-hub.vercel.app), production deployment `dpl_EPUKWxuCnxaMQgA6FNYRgXkr7PAz`. Its `/api/health` endpoint reports the current Hub, chain 61999, reachable RPC, and available Hub code. After deployment, Home, Field list, dossier detail, real-data autofill, Method, and Vault were checked in a browser; all principal routes returned HTTP 200.

The browser used for this verification had no connected wallet. The live research-to-payout lifecycle therefore ran through GenLayerJS and is not described as browser-originated. The frontend persists multiple pending parent receipts and verifies outgoing child receipts and the recipient balance delta before reporting payout success. It checks for an EOA recipient because the native payout interface is for EOAs. A finalized external child failure cannot be safely auto-recredited by the contract: the protocol currently provides no authenticated failure callback from that external message, and automatic retry could double-pay if a prior child later succeeds.
