# Deployment

## Secure bootstrap

Noema’s circular authentication requirement is resolved without mutable administration:

1. deploy `NoemaHub` with empty worker addresses;
2. deploy `SourceWitness` with the Hub address;
3. deploy `VerdictEngine` with the Hub address;
4. call `NoemaHub.configure` once;
5. the Hub clears its bootstrapper and permanently rejects reconfiguration.

The deployment script refuses any chain other than Studionet `61999`.

```bash
npm install
genlayer network set studionet
genlayer network info
genlayer deploy
```

After deployment, add the Hub address to `frontend/.env.local`:

```text
NEXT_PUBLIC_NOEMA_HUB_ADDRESS=0x...
```

Then verify:

```bash
genlayer schema <HUB_ADDRESS>
genlayer schema <WITNESS_ADDRESS>
genlayer schema <ENGINE_ADDRESS>
genlayer call <HUB_ADDRESS> get_stats
```

The deployment output is written to `deployments/studionet.json`. Treat failed transactions as evidence to inspect with `genlayer receipt` and `genlayer trace`; never redeploy blindly.

## Production release

The currently verified Studionet deployment is:

| Component | Address | Deployment transaction |
|---|---|---|
| NoemaHub | `0xfFf9A84A6256DCF2A971674E3bd21956b4072f12` | `0x911153644f8a09d69771592ed57db0143dec7c75169f43242763a0d5d2505900` |
| SourceWitness | `0x83c9c59Ebf368C01468d7E8eD257ae04111bA9c5` | `0x4aa283d83a1426a2e5d96bdc9e7413daaeb287af29e5a8cb042fb13073d379d2` |
| VerdictEngine | `0x2E9eD1d764Bfda225443AC70Bb3EE613Fd97Ba30` | `0xf150f120e0093813e1a710051cbb4f6cf83911e9bfa96e9e3e7c0d88d72c2243` |

The one-time binding transaction is `0x5a0261d2e89c8f80b9b8f793ef33f4cb9fe90b8c1facc49e50ca9d3ce56bbd5a`. This release enables native payouts through the EVM recipient interface. The exact deployed sources are verified against RPC-returned code in `deployments/studionet.json`.

## Real-network acceptance test

The acceptance harness uses two distinct funded accounts and real first-party files from the official `openai/codex` repository:

```bash
genlayer account use cw-milestone
NOEMA_E2E_PHASE=sponsor genlayer deploy

genlayer account use eventweaver
NOEMA_E2E_PHASE=research genlayer deploy

genlayer account use eventweaver
NOEMA_E2E_PHASE=withdraw genlayer deploy
```

The CLI scans the `deploy/` directory for scripts. `00_cleanup.ts` removes only stale generated bundles before the TypeScript test harness runs; keep generated `.compiled.js` files out of source control and do not pass the harness as `--contract`.

The current end-to-end StudioNet run created `noema-4`, attested the official Git tree API baseline and raw LICENSE text, sealed/revealed `note-2`, and resolved `POSITION_A` with only `note-2` decisive and a counterfactual `UNRESOLVED` outcome without it. The researcher withdrew `0.0022 GEN` in one external transfer (accrued across two resolved dossiers on this Hub). Parent `0x117b537038f9faacaf069f1c4d1fbeed5731ab0940b7f132b2469694f58c74c6` emitted finalized child `0xd5e57ca9a0c6fa53ed73901d919a7cf56ba15e612be9b180a9c16a7a2a431cf0`; the child names the researcher wallet, reports `value_credited=true`, and carries exactly `2200000000000000` wei. Wallet balance moved from `10030099999999999997` to `10032299999999999997`, Hub credit moved from `2200000000000000` to `0`, and accounting remained true. A second finalized withdrawal attempt failed with `[EXPECTED] no credit available` and emitted no child. Full transaction evidence is recorded in `deployments/e2e-studionet.json`.

The browser E2E inspected the production home, field list, dossier detail, autofill form, method notes, and vault. The real-data autofill was clicked and field values were verified. The browser session had no connected wallet, so the live research and payout were executed with the two funded StudioNet accounts through GenLayerJS rather than claimed as browser-originated transactions.

The frontend and backend API are deployed at [neoma-hub.vercel.app](https://neoma-hub.vercel.app). Its `/api/health` endpoint verifies the RPC, chain ID, and deployed Hub code. The browser withdrawal flow persists multiple pending parent receipts and verifies each external child receipt and wallet balance delta before displaying payout success. Before submitting a withdrawal, the UI now checks `eth_getCode` and refuses contract-wallet recipients; the native payout interface is intended for EOAs.

Recovery boundary: browser storage can resume an interrupted or still-pending parent/child receipt, and the Hub prevents duplicate credit withdrawal. The protocol does not currently send an authenticated failure callback from an external EVM child back to the Intelligent Contract. Therefore a finalized external child with `value_credited=false` cannot be safely re-credited automatically by this deployment; blindly retrying could pay twice if the earlier child later succeeds. The balance preflight, EOA-only frontend guard, persistent receipt, and successful live child reduce this risk, but they do not provide arbitrary failed-external-transfer recovery. Do not describe that edge case as fully recovered.
