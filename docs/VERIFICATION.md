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

The published manifest parity vector is:

```text
dossier: noema-1
evidence: base-1, note-1
manifest root: 9f18409690f81c54c257d64c0e15572e7c77674afa5c7707de57e4411c87f000
```

`contracts/domain.py`, `NoemaHub`, and `VerdictEngine` all hash the same canonical evidence array directly.

## StudioNet resolution proof

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

This demonstrates that the current StudioNet backend does not deliver this contract-originated value message to an ordinary wallet, even though the pinned GenVM SDK exposes `emit_transfer`. Noema therefore disables withdrawal in production by default. The UI will enable it only when `NEXT_PUBLIC_NATIVE_PAYOUTS_ENABLED=true` is deliberately set after a network-level transfer test passes.

The Hub includes a failed-message recovery hook, but this StudioNet execution did not schedule that callback. This is retained as an explicit network blocker, not reported as a successful payout.
