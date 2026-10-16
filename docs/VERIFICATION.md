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

The current local run passed 38 direct contract tests and 13 frontend tests, plus frontend typecheck and optimized production build. Coverage includes authenticated callbacks, contribution necessity, candidate-independent verdict rejection, the executable 12-ID decisive bound, HTTP status handling, requested-versus-verified provenance, manifest-root parity, timeout recovery, queue and lifetime bounds, payout failure accounting, exact parent/child receipt matching, and the fixed-hash read-only payout gateway.

At commit `d162a9922353c5de4194ee79d24a807818218413`, the same release commands passed locally: 19 direct contract tests, 3 frontend tests, both TypeScript checks, and the optimized Next.js production build. GitHub Actions run `38856609580` did not allocate a runner or execute a single step. Both jobs contain GitHub's annotation: `The job was not started because your account is locked due to a billing issue.` Restoring hosted CI therefore requires the repository owner to resolve the GitHub account billing lock; the workflow itself remains reproducible through the commands above.

The final release-record push, commit `4ff60e6`, triggered [GitHub Actions run 38899527179](https://github.com/zoefunds/Noema-hub/actions/runs/38899527179). Both jobs failed before starting and report `steps: []`; there is no hosted green run to claim. Local gates passed in this environment: 38 contract tests, 13 frontend tests, 4 signer-safety tests, typecheck, and production build. The funded lifecycle below was run through GenLayerJS, not initiated from a connected browser wallet.

The published manifest parity vector is:

```text
dossier: noema-1
evidence: base-1, note-1
manifest root: 9f18409690f81c54c257d64c0e15572e7c77674afa5c7707de57e4411c87f000
```

`contracts/domain.py`, `NoemaHub`, and `VerdictEngine` all hash the same canonical evidence array directly.

## StudioNet resolution proof

The current deployed addresses and exact source hashes are recorded in `deployments/studionet.json`. The fully completed live resolution is recorded in `deployments/e2e-studionet.json` for dossier `noema-1`. Older deployment attempts and their incomplete states are historical records, not the current deployment or current acceptance result.

The full harness log is retained in `deployments/e2e-studionet.json`; the concise, current-run acceptance proof is `deployments/studionet-e2e-latest.json`. The release resolved a real public question using first-party files from the official `openai/codex` repository:

- dossier `noema-1`;
- sponsor/open transaction `0x08918cdf05c07eb8afb588517d88d9523a14cef68c4ab42aaa730b0d9ea30158`;
- commitment transaction `0x4c78cf9747969dd0add21924df553d38bfdbfeb8de2b418b50165b0d13d14bac`;
- disclosure transaction `0x53630d5c9944e4ea0793e89bf10cf1edbb934e1e008dba988e66f4599e1f9c83`;
- outcome `POSITION_A`;
- decisive IDs `["note-1"]`;
- counterfactual outcome without `note-1`: `UNRESOLVED`;
- researcher credit before withdrawal: `1100000000000000` atto GEN; after: `0`;
- accounting and solvency invariants after withdrawal: true;
- duplicate withdrawal rejected; temporary sponsor's unused `0.002 GEN` swept with a finalized transaction.

The candidate and baseline both have HTTP status 200 and content digests. Requested origin is recorded as requested provenance; authenticated canonical URL, publisher, redirect chain, and verified response origin remain empty because the current fetch interface does not prove them.

## Native payout proof

The prior internal-message attempt on an earlier deployment failed and its callback was not observed. That failure motivated switching to the EVM recipient interface for EOAs. The current payout and recovery path was tested end to end:

- parent withdrawal `0x05274e66eb4093cb16e48b1a7b8f3080bf92ff185a689ca91b67300456739120` finalized;
- emitted child `0xc97a20a6510b2597b37545acecc77f4e8de9334c54faa77cc07727f5f2be2661` finalized with `value_credited=true`;
- reconciliation transaction `0x610f43f82eb842592891fa3554d2ff73f728d705de3bd3eb1e3ae2705ea5a829` finalized with authoritative Hub status `DELIVERED` and exact parent/child IDs;
- child recipient is `0x7401c129EDfc26E68FE19309fE461eb3Db1058Eb`; the transfer was exactly `1100000000000000` atto GEN;
- recipient balance changed from `999000000999876277587324887999999998992` to `999000000999876277587325987999999998992` atto GEN;
- Hub credit changed from `1100000000000000` to `0`; `accounting_ok=true`, `solvent_ok=true`, and a duplicate withdrawal was rejected.

The earlier `0.0011 GEN` from Hub `0x49Cb…FcF3` is not recoverable through Noema: its old immutable Hub now reports zero credit, the child did not credit the EOA, and that deployment has no user-callable recovery method. The network record does not establish whether GenLayer operators can recover the value at protocol level. Full evidence is retained in `deployments/legacy-withdrawal-failure.json`.

The freshly deployed Hub's `reconcile_withdrawal` asks each validator to independently fetch the exact finalized parent and child transaction records. It checks the parent sender, Hub destination, withdraw calldata, creation time, exact one-off recipient/value message, plus the child's parent link, sender, recipient, value, finality, and boolean `value_credited`. A verified failed child restores the user's claim and records any resulting backing shortfall; further withdrawals remain blocked until a sponsor recapitalizes the Hub. No timeout or user-directed re-credit is allowed.

The contract uses the fixed-method `/api/payout-receipt` GET gateway because GenVM validators could not obtain a usable response from the public RPC's POST endpoint. The gateway accepts only a 32-byte hash and projects a bounded set of receipt fields; it has no write method or wallet credentials. This remains consensus-replayed provider data, not a cryptographic inclusion proof, and depends on both the Vercel gateway and StudioNet RPC. The delivered-child path was exercised live. The failed-child refund branch is covered by deterministic contract tests but has not been induced on-chain on this release.

The production browser pages (Home, Field list, real-data dossier creation autofill, dossier detail, Method, and Vault) were smoke-tested against the new Hub; the health endpoint returned chain 61999, reachable RPC, and deployed Hub code. The funded transaction lifecycle was executed through GenLayerJS, not initiated by a connected browser wallet. Production payout parent and child receipt projections were also checked directly through the deployed API.
