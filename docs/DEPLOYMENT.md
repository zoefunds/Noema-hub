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
| NoemaHub | `0x99aaE7794Be988833CbC536cEaaE8e94E8eB1c5B` | `0x7497c6b5070df03e55e314dc5bf1c9a9fcd596fdf5cbfbb09a638fcb9639efd7` |
| SourceWitness | `0x9aAe228eAaf7D4806498F0c189320Ec89d7069d0` | `0x27fe90f8b0e1a27d14c9e217206790110219e0b4084f9e7bd00fd689a2b36b27` |
| VerdictEngine | `0xB9fBD0e65275853f8ba45E4Eb0502FB8c3187bbA` | `0x00278011cc0762cdf469a520738cef6e70a03522aeb981c6850efc0923b305b3` |

The one-time binding transaction is `0x768f91cd244d2caf791d6c32c1268e13bd30df3dcddaa22172b65b511335b6e8`. This fresh release enables native payouts through the EVM recipient interface. The exact deployed sources are verified against RPC-returned code in `deployments/studionet.json` (Hub SHA-256 `4020e8ed…`, Witness `0f4ef7d4…`, Engine `7085da39…`).

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

The prior end-to-end acceptance run on the previous Hub created `noema-4`, attested the official Git tree API baseline and raw LICENSE text, sealed/revealed `note-2`, and resolved `POSITION_A` with only `note-2` decisive and a counterfactual `UNRESOLVED` outcome without it. The researcher withdrew `0.0022 GEN` in one external transfer (accrued across two resolved dossiers on that Hub). Parent `0x117b537038f9faacaf069f1c4d1fbeed5731ab0940b7f132b2469694f58c74c6` emitted finalized child `0xd5e57ca9a0c6fa53ed73901d919a7cf56ba15e612be9b180a9c16a7a2a431cf0`; the child names the researcher wallet, reports `value_credited=true`, and carries exactly `2200000000000000` wei. Wallet balance moved from `10030099999999999997` to `10032299999999999997`, Hub credit moved from `2200000000000000` to `0`, and accounting remained true. A second finalized withdrawal attempt failed with `[EXPECTED] no credit available` and emitted no child. This is historical evidence for the previous deployment, not a claim that the new Hub has already completed the lifecycle.

The current Hub/Witness/Engine were freshly deployed and bound on 2026-10-16, and RPC-returned code hashes match all three source files. The Vercel production deployment `dpl_AK1vXjLn36pqUgN8Sn52yGPSZhFv` is READY and points to the new Hub; health returned chain 61999 and Hub code available at `2026-10-16T08:15:53.049Z`. Live browser checks cover the home, empty production field, real-data autofill form, Method, and Vault. The new Hub is intentionally empty after redeployment. Its funded sponsor-to-withdrawal E2E is pending secure unlock of the sponsor account keystore; do not treat the previous deployment's payout as proof for this fresh state.

The browser E2E inspected the production home, field list, dossier detail, autofill form, method notes, and vault. The real-data autofill was clicked and field values were verified. The browser session had no connected wallet, so the live research and payout were executed with the two funded StudioNet accounts through GenLayerJS rather than claimed as browser-originated transactions.

The frontend and backend API are deployed at [neoma-hub.vercel.app](https://neoma-hub.vercel.app). Its `/api/health` endpoint verifies the RPC, chain ID, and deployed Hub code. The browser withdrawal flow persists multiple pending parent receipts and verifies each external child receipt and wallet balance delta before displaying payout success. Before submitting a withdrawal, the UI now checks `eth_getCode` and refuses contract-wallet recipients; the native payout interface is intended for EOAs.

Recovery boundary: browser storage can resume an interrupted or still-pending parent/child receipt, and the Hub prevents duplicate credit withdrawal. The protocol does not currently send an authenticated failure callback from an external EVM child back to the Intelligent Contract. Therefore a finalized external child with `value_credited=false` cannot be safely re-credited automatically by this deployment; blindly retrying could pay twice if the earlier child later succeeds. The balance preflight, EOA-only frontend guard, persistent receipt, and successful live child reduce this risk, but they do not provide arbitrary failed-external-transfer recovery. Do not describe that edge case as fully recovered.
