# Verification record

This record distinguishes deterministic local checks, the current source-matched StudioNet release, and historical evidence. A payout is successful only when the Hub's canonical-RPC reconciliation verifies finalized parent/child execution, exact recipient and amount, and the recipient balance delta.

## Local verification

From the repository root (Python 3.12+ and Node.js 20+):

```bash
python -m pip install -r requirements.txt
npm install
npm run ci
```

The current local release check passed 55 direct contract tests, 4 sponsor-key safety tests, and 13 frontend tests, plus TypeScript checking, the optimized frontend build, GenVM linting of all three contracts, `pip check`, and dependency audits with no known vulnerabilities. Coverage includes complete-body inspection past the former 24,000-character limit; strict literal-boolean admissibility parsing; rejected redirects, unsupported publishers/origins, contradictory evidence, malformed replies, and prompt injection; frozen sponsor rules and FIFO handling; conflicting-evidence consensus; deadline rollback; forged/mismatched receipts; and stateful receipt replay and duplicate-credit rejection.

GitHub Actions is configured in [`.github/workflows/quality.yml`](../.github/workflows/quality.yml). No hosted-green claim is made: on 2026-10-20 GitHub stopped the release-evidence run [`39456409579`](https://github.com/zoefunds/Noema-hub/actions/runs/39456409579) before either job executed because of an owner-controlled billing authorization failure. The workflow-equivalent checks above passed locally; hosted CI must be rerun after the account billing issue is resolved.

## Current source-matched StudioNet release

[`deployments/studionet.json`](../deployments/studionet.json) records a clean StudioNet `61999` deployment from commit `2391ac15d210e8d505cb7bd3c8e08d73788883b3`. The deployer retrieved each deployed contract through GenLayerJS `getContractCode`, required SHA-256 equality with the checked-in source, and checked finalized execution before writing the manifest.

| Contract | Address | Deployed source SHA-256 |
|---|---|---|
| NoemaHub | `0xcBcfF1dc3FD979fb48d65E078Ca7a8fcf98483e4` | `4beaa1487527b6671d14ecdaacc8273ad577a806b3769f85163d24222b1449d0` |
| SourceWitness | `0x9D2CF136821F01369fbBc462F5fE868670c92785` | `ba20fe8715ee1ad1eecd8e6ead0c0ff3f4d58d0d640dc1b88e2dd2e4de06f713` |
| VerdictEngine | `0x22C980402f1bF4D15333aF4CE5002A3f19DC9eA9` | `eb5373a68b165172c18433bb10c48c864e8ccdba935fb64fbd94cfc06a884e9a` |

Deployment transactions are `0x8fbb85ace3d58ec90b4eaaa1d89e3bae77699cbeb4fc8abba6d35c6cfb0d57ca`, `0xcae8b91b3d1d86a5e36ab649250055e4e55c05845e50295950ad1e5a8c20b40a`, and `0x6a64467cbabe93f52479eafe977f0d5356f3f453d04e3135115352b5a6fbbb73`; the immutable worker binding is `0x61200c1f911a2be12ba93a48c5c1080bfac976b46904f64de182886d603ff532`.

## Fresh StudioNet lifecycle

The `freshRedeploymentRun` in [`deployments/e2e-studionet.json`](../deployments/e2e-studionet.json) is the current-release CLI/GenLayerJS record. It resolved `noema-1` as `POSITION_A` using a frozen rule root and a deterministic, authenticated-support closure basis; removing that support makes the result unresolved.

The researcher received `1100000000000000` atto GEN (`0.0011 GEN`). Withdrawal parent `0xa878680d9a22f17e2fc9ff51053660a053e3e32db01474e2a1d0507544b9b4a0` and finalized child `0x1a3fc2e900400c3a8f9961f01621901ff2afa7b91fda2a137dba90e456cc8d63` were reconciled as `DELIVERED`; the Hub credit changed from that amount to zero and the recipient balance rose from `452499999967045000` to `453599999967045000` atto GEN. The record also proves duplicate withdrawal rejection, zero residual sponsor balance, accounting, and solvency.

The timeout artifact [`deployments/studionet-timeout-rollback.json`](../deployments/studionet-timeout-rollback.json) is retained as a real asynchronous StudioNet timeout demonstration, but it belongs to an earlier deployment and is not presented as current-release evidence. Likewise, [`deployments/studionet-browser-wallet-verification.json`](../deployments/studionet-browser-wallet-verification.json) is historical only.

## Browser-wallet status

The current production site is [neoma-hub.vercel.app](https://neoma-hub.vercel.app), deployment `dpl_EFmyYfwdwc4Nszw9U1U7m2PUg8qy`, configured for the current Hub. A browser-wallet account successfully opened current-Hub dossier `noema-2` in finalized transaction `0xcbff89cf95f8886ef66b8c3365e03abef0e7da8c8c07ff3afb1877d0cd3c8bf9`. A later browser audit caught a stale pending seal request before signing; it was canceled, and the actual `neoma-hub` project configuration was corrected and redeployed.

That browser-originated dossier is still `OPEN`. A current-release browser seal, reveal, witness, verdict, reward, withdrawal, and reconciliation sequence has **not** been claimed or recorded. Completing it requires the wallet holder's just-in-time confirmation for the real bond and withdrawal transactions.

## Security boundaries

SourceWitness authenticates bytes, request/response binding, complete-body digest and size, exact support, and allowlisted immutable content-addressed origins. It does not turn an ordinary fetched web page into cryptographic proof of a publisher's identity or publication time; policy requiring those properties rejects the source unless the required origin authentication is available. Redirects, origin conflicts, unsupported publisher claims, and oversized or otherwise unauthenticated decisive material fail closed.

The Vercel receipt endpoint is a UI projection only. The Hub's `reconcile_withdrawal` validates finalized canonical StudioNet parent/child records directly under validator replay, including linkage, sender, recipient, amount, calldata, finality, `value_credited`, and single-use receipt consumption. A verified failure can recredit only once and withdrawals remain blocked when the resulting backing is insolvent.
