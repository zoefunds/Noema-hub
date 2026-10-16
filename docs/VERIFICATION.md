# Verification record

This record separates reproducible deterministic checks from public-network observations. A finalized transaction is counted as successful only when its GenVM execution result is also successful and the expected state is read back from the contract.

## Reproduce locally

Run from the repository root with Python 3.12+ and Node.js 20+:

```bash
pip install -r requirements.txt
python -m pytest tests/direct -q

npm ci
npx tsc --noEmit

npm --prefix frontend ci
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

The direct suite covers authenticated callbacks, contribution necessity, candidate-independent verdict rejection, the executable 12-ID decisive bound, HTTP 2xx enforcement, requested-versus-verified provenance, manifest-root parity, timeout recovery, queue and lifetime bounds, internal-message error recovery, and exact finalized parent/child payout receipt matching for both credited and failed children. Frontend tests cover successful execution receipts, failed/non-final receipts, payout receipt matching, and pending record preservation.

At commit `d162a9922353c5de4194ee79d24a807818218413`, the same release commands passed locally: 19 direct contract tests, 3 frontend tests, both TypeScript checks, and the optimized Next.js production build. GitHub Actions run `38856609580` did not allocate a runner or execute a single step. Both jobs contain GitHub's annotation: `The job was not started because your account is locked due to a billing issue.` Restoring hosted CI therefore requires the repository owner to resolve the GitHub account billing lock; the workflow itself remains reproducible through the commands above.

After the payout and HTTP retry changes, the same local gates passed again: 32 direct contract tests, 4 frontend tests, both TypeScript checks, and the optimized production build. The latest hosted run, [38865302473](https://github.com/zoefunds/Noema-hub/actions/runs/38865302473), again failed before either job started; GitHub's annotations explicitly say the account is locked due to a billing issue, and both jobs have zero steps. This is not a code/test failure, but hosted CI cannot be reported green until the repository owner resolves the account billing lock. The funded live lifecycle in this artifact was run through GenLayer JS, not through an injected browser wallet; the deployed browser flow now checks the outgoing child and persists pending verification state, but the browser-originated lifecycle remains unverified because desktop browser automation permissions were unavailable.

The published manifest parity vector is:

```text
dossier: noema-1
evidence: base-1, note-1
manifest root: 9f18409690f81c54c257d64c0e15572e7c77674afa5c7707de57e4411c87f000
```

`contracts/domain.py`, `NoemaHub`, and `VerdictEngine` all hash the same canonical evidence array directly.

## StudioNet resolution proof

The current deployed addresses and exact source hashes are recorded in `deployments/studionet.json`. The fully completed live resolution is recorded in `deployments/e2e-studionet.json` for dossier `noema-4`; its exact finalized payout is also described below. Older deployment attempts and their incomplete states are historical records, not the current deployment or current acceptance result.

The complete machine-readable record is in `deployments/e2e-studionet.json`. The final hardened deployment resolved a real public question using first-party files from the official `openai/codex` repository:

- dossier `noema-1`;
- baseline transaction `0xd6cacc10849f2232e95cdb3e77ca7b89705ca240cf303dd7108560facd8a4d2f`;
- commitment transaction `0xcfccc6b5c8796ee20e90899f23620f08e22f8dcfe88e81d3ae331133ba6bdb18`;
- disclosure transaction `0xc1149846acb72d33d7f3e954756c5455bc6e7e4c3a704581033bb56ec540232b`;
- outcome `POSITION_A`;
- decisive IDs `["note-1"]`;
- counterfactual outcome without `note-1`: `UNRESOLVED`;
- researcher credit: `1100000000000000` atto GEN;
- accounting invariant: true.

The candidate and baseline both have HTTP status 200 and content digests. Requested origin is recorded as requested provenance; authenticated canonical URL, publisher, redirect chain, and verified response origin remain empty because the current fetch interface does not prove them.

## Native payout proof

The prior internal-message attempt on an earlier deployment failed and its callback was not observed. That failure motivated switching to the EVM recipient interface for EOAs, which the current official GenLayer documentation specifies for external chain-layer value transfers. The active payout deployment was then tested end to end:

- parent withdrawal `0x0770d17f04c2a805aef970769808f1f32e4cffeaa09c4866256bd4d2eb31121c` finalized with successful GenVM execution;
- emitted child `0xf3b35e84c583474418c87a793c0214fedf09a0e315654447b1f7ef9eacab27d2` finalized with `value_credited=true`;
- child recipient is `0x7452084e1cf767bf19c743051cff27d9f7a87a4d` and value is `1100000000000000` atto GEN;
- recipient balance changed from `10029199999999999997` to `10030299999999999997` atto GEN;
- Hub credit changed from `1100000000000000` to `0` and `accounting_ok=true`;
- a second withdrawal with no credit was rejected.

The earlier `0.0011 GEN` from Hub `0x49Cb…FcF3` is not recoverable through Noema: its old immutable Hub now reports zero credit, the child did not credit the EOA, and that deployment has no user-callable recovery method. The network record does not establish whether GenLayer operators can recover the value at protocol level. Full evidence is retained in `deployments/legacy-withdrawal-failure.json`.

The existing deployed Hub remains immutable and has no payout-recovery method; its old failed credit therefore remains unrecoverable through that address. The updated source adds permissionless `reconcile_withdrawal`, which asks each validator to independently re-fetch the exact finalized StudioNet parent and child transaction records. It checks the parent sender, Hub destination, withdraw calldata, creation time, exact one-off recipient/value message, plus the child's parent link, sender, recipient, value, finality, and boolean `value_credited`. A verified failed child restores the user's claim and records any resulting backing shortfall; further withdrawals remain blocked until a sponsor recapitalizes the Hub. No timeout or user-directed re-credit is allowed.

This is consensus-replayed evidence from the configured StudioNet RPC, not a cryptographic inclusion proof. Validators compare independently fetched records, but this design still depends on that RPC's integrity and availability; the new recovery code must be freshly deployed and its live failed-child branch exercised before it can be called an active recovery feature. The frontend source preserves pending receipts, submits reconciliation, and checks final Hub state and the wallet balance before reporting a successful payout.

The deployed browser version distinguished parent success from actual child delivery by requiring a finalized credited child, wallet balance increase, and fresh Hub credit readback. The current source extends that flow with consensus reconciliation for delivered and failed child receipts. A desktop browser-originated full lifecycle was not exercised; the funded network lifecycle was executed through GenLayerJS.
