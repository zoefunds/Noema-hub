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

The direct suite covers authenticated callbacks, contribution necessity, candidate-independent verdict rejection, the executable 12-ID decisive bound, HTTP 2xx enforcement, requested-versus-verified provenance, manifest-root parity, timeout recovery, queue and lifetime bounds, and failed outbound-transfer recovery structure. Frontend tests cover modern and legacy successful execution receipts as well as finalized execution errors and non-final receipts.

At commit `d162a9922353c5de4194ee79d24a807818218413`, the same release commands passed locally: 19 direct contract tests, 3 frontend tests, both TypeScript checks, and the optimized Next.js production build. GitHub Actions run `38856609580` did not allocate a runner or execute a single step. Both jobs contain GitHub's annotation: `The job was not started because your account is locked due to a billing issue.` Restoring hosted CI therefore requires the repository owner to resolve the GitHub account billing lock; the workflow itself remains reproducible through the commands above.

After the payout and HTTP retry changes, the same local gates passed again: 32 direct contract tests, 4 frontend tests, both TypeScript checks, and the optimized production build. Hosted CI remains subject to the recorded account billing lock. The funded live lifecycle in this artifact was run through GenLayer JS, not through an injected browser wallet; the deployed browser flow now checks the outgoing child and persists pending verification state, but the browser-originated lifecycle remains unverified because desktop browser automation permissions were unavailable.

The published manifest parity vector is:

```text
dossier: noema-1
evidence: base-1, note-1
manifest root: 9f18409690f81c54c257d64c0e15572e7c77674afa5c7707de57e4411c87f000
```

`contracts/domain.py`, `NoemaHub`, and `VerdictEngine` all hash the same canonical evidence array directly.

## StudioNet resolution proof

The current production safety deployment is Hub `0x8AF8731fC1143010dD9b21e8B357A0Ca9D1644b6`, Witness `0x366815EC7f963786E8A0d6Ec7c10bb38aE989D0b`, and Engine `0x3baDCAf04b067B212Cd51fBf8FA95ef8DC209796`. Its sponsor phase reached `noema-3`; repeated researcher calls encountered a StudioNet receipt with `FINALIZED` but no execution-result field at `seal_disclosure`, so this new deployment is not represented as a completed resolution until that receipt is independently replayed. The earlier completed resolution remains preserved in Git history and the prior acceptance artifact.

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

The browser flow now distinguishes parent success from actual child delivery. It requires a finalized child receipt matching the recipient and amount, `value_credited=true`, an observed wallet increase of at least the payment amount, and a fresh Hub credit readback of zero before displaying success. This browser code is deployed; a desktop browser-originated full lifecycle was not exercised because desktop accessibility/screen-recording permissions remained pending during this run. The real funded network lifecycle was executed through the GenLayer client.
