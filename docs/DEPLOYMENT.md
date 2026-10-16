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
| NoemaHub | `0x6592007a9e33CbFD99A62e0979a71149CF6684B4` | `0x8c36b3fa54bb20d27b0a3b78b14143a5d0650a6182ea273e497b56cb86c9fd1d` |
| SourceWitness | `0x6d04F2a47B6a2EE5128a87A839127Fdcf0E15b28` | `0xb3adc6f25a719c22045068c4af8b748ecf7a0803dfff7979942fe231929967b3` |
| VerdictEngine | `0x16262D365832F73Fdc4095e4942872166fdF39E0` | `0x03069d4bfccf5c97c15cbd1d6d34a2dc59deaa16e77da3862e058d2355bbce0b` |

The one-time binding transaction is `0x987e8bcb6d3d76aa494d2c6b1317d8d75f8915789404bd66ab0353b68bfbe934`. This release enables native payouts through the EVM recipient interface. The exact deployed sources are verified against RPC-returned code in `deployments/studionet.json`.

## Real-network acceptance test

The acceptance harness uses two distinct funded accounts and real first-party files from the official `openai/codex` repository:

```bash
genlayer account use cw-milestone
NOEMA_E2E_PHASE=sponsor genlayer deploy

genlayer account use eventweaver
NOEMA_E2E_PHASE=research genlayer deploy
```

The verified run created `noema-1`, sealed and revealed `note-1`, fetched the official README and LICENSE, resolved `POSITION_A`, credited the researcher `0.0011 GEN`, and ended with `accounting_ok=true`. Parent withdrawal `0x0770d17f04c2a805aef970769808f1f32e4cffeaa09c4866256bd4d2eb31121c` emitted finalized child `0xf3b35e84c583474418c87a793c0214fedf09a0e315654447b1f7ef9eacab27d2` with `value_credited=true`. The wallet increased by exactly 0.0011 GEN, Hub credit became zero, and a duplicate withdrawal was rejected. Transaction hashes, provenance digests, manifest roots, decisive IDs, and the final records are stored in `deployments/e2e-studionet.json`.

An earlier internal-message withdrawal attempt on a prior deployment failed because an EOA was treated as an Intelligent Contract. The current deployment uses the documented EVM recipient interface and has a successful finalized external payout, with complete parent/child receipts in the acceptance artifact.

The frontend is deployed at [neoma-hub.vercel.app](https://neoma-hub.vercel.app). Its `/api/health` endpoint verifies the RPC, chain ID, and configured Hub. Browser withdrawals also verify the child receipt and actual wallet balance change after the parent finalizes.
