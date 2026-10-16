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
| NoemaHub | `0x8AF8731fC1143010dD9b21e8B357A0Ca9D1644b6` | `0x4f85531f0d2f72390e475f3e9b3ed166578fd72315c74a38271959025ab511c2` |
| SourceWitness | `0x366815EC7f963786E8A0d6Ec7c10bb38aE989D0b` | `0x6d8a2f5af69b505ed32a7122db18e5541f52e2e918657d3acf37a3150616e4fd` |
| VerdictEngine | `0x3baDCAf04b067B212Cd51fBf8FA95ef8DC209796` | `0xa594579e628974bc7e0fc8a48830a8416cd45803af882264ce2078a7faacc86c` |

The one-time binding transaction is `0x824eba1f16717e10b2037c6e91b4ca66e6b82ff0ea3338a7aefd2473bdc93f74`. This release has native payouts disabled at the Hub until StudioNet proves EOA transfer delivery.

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
