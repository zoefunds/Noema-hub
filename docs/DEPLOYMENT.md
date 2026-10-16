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
| NoemaHub | `0x49Cb64ba7CA953ffABE72eF34841067532FBFcF3` | `0x0efb2045c491d1eef4742d2a5de96402130262fbfbc0134215da8f5139008cd0` |
| SourceWitness | `0x8B86CA98cc0bfaCf7995578DAB10F956C275c82c` | `0x555c97ff32d0b538f3d6aa178a28f1cc50c17c871aa2ac2e9bfa4548b1407965` |
| VerdictEngine | `0xC886a61cc0402Db8b71ec0405a658D0e32b2120D` | `0x58c4ffa340039378e8e1c3f9d410362f335daeb434e8912000b89bfcb7e95658` |

The one-time binding transaction is `0xc6ba6e1c57cfd2d496a0f6e9cec181d6b365643fc2a4bca3123efcfe604cb98e`.

## Real-network acceptance test

The acceptance harness uses two distinct funded accounts and real first-party files from the official `openai/codex` repository:

```bash
genlayer account use cw-milestone
NOEMA_E2E_PHASE=sponsor genlayer deploy

genlayer account use eventweaver
NOEMA_E2E_PHASE=research genlayer deploy
```

The verified run created `noema-1`, sealed and revealed `note-1`, fetched the official README and LICENSE, resolved `POSITION_A`, credited the researcher `0.0011 GEN`, and ended with `accounting_ok=true`. Transaction hashes, provenance digests, manifest roots, decisive IDs, and the final records are stored in `deployments/e2e-studionet.json`.

The verdict records `contribution_required=true` and `counterfactual_outcome=UNRESOLVED`. A withdrawal was also exercised. Parent transaction `0xfe3b…6877` finalized successfully and emitted child `0xbc70…b744` for `0.0011 GEN`, but StudioNet finalized the child with `Contract <researcher EOA> not found`, `value_credited=false`, and no recipient balance increase. Native payout is therefore paused in production and is not claimed as complete. The full failure record is retained in the same artifact for runtime maintainers.

The frontend is deployed at [neoma-hub.vercel.app](https://neoma-hub.vercel.app). Its `/api/health` endpoint verifies the RPC, chain ID, and configured Hub.
