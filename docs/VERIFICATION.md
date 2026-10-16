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

## Native payout runtime observation

A real withdrawal attempt was executed rather than simulated:

- parent withdrawal: `0xfe3b17000d5b177695453a50a772f330d296c996210bcfa32649966e9e8d6877`, finalized successfully;
- emitted transfer: `0xbc706f67966cff0a9f407748c1d09f126b153a182fb936340853f9e88156b744`;
- amount: `1100000000000000` atto GEN;
- child status: `FINALIZED`;
- child execution: `ERROR`;
- runtime result: `Contract 0x7452084E1Cf767bf19C743051cFf27D9F7A87a4D not found`;
- `value_credited=false`;
- recipient balance before and after: `10029599999999999997` atto GEN.

This demonstrates that the current StudioNet backend does not deliver this contract-originated value message to an ordinary wallet, even though the pinned GenVM SDK exposes `emit_transfer`. Noema therefore disables withdrawal in production by default at both the Hub and UI layers. A future deployment may enable it only after network-level wallet-delivery and failed-callback tests pass.

The Hub includes a failed-message recovery hook, but this StudioNet execution did not schedule that callback. This is retained as an explicit network blocker, not reported as a successful payout.
