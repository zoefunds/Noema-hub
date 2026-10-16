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
| NoemaHub | `0xe4C8fCeD5Ba04019A4816D7F51Daa3EAacc26E40` | `0x8e849533d50b3fa387280f09e884593f1ef9f9a354f21482c4b60536bdaa5046` |
| SourceWitness | `0x2988f0021A834385c9Cf33B7687C8b97B59D3Ea0` | `0x5255394e8c301896ae497892be9ed2c5d54cc76d3ada56f15d120b4039bf9b0d` |
| VerdictEngine | `0x6C3BD278F19AAcbd91b776D7DF8883C01f738d96` | `0x72607c2d668d5ad61326376ae67ea8abd1b53822a30a4ed830b195c3f8962d65` |

The one-time binding transaction is `0xebcc0275b54ad4a95d19a9c9cfd539640a21ae1c4fa0e668871bc26aa2ccb14c`.

## Real-network acceptance test

The acceptance harness uses two distinct funded accounts and real first-party files from the official `openai/codex` repository:

```bash
genlayer account use cw-milestone
NOEMA_E2E_PHASE=sponsor genlayer deploy

genlayer account use eventweaver
NOEMA_E2E_PHASE=research genlayer deploy
```

The verified run created `noema-1`, sealed and revealed `note-1`, fetched the official README and LICENSE, resolved `POSITION_A`, credited the researcher `0.0011 GEN`, and ended with `accounting_ok=true`. Transaction hashes, provenance digests, manifest roots, decisive IDs, and the final records are stored in `deployments/e2e-studionet.json`.

The frontend is deployed at [neoma-hub.vercel.app](https://neoma-hub.vercel.app). Its `/api/health` endpoint verifies the RPC, chain ID, and configured Hub.
