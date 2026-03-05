# Runbook: Safe Model Release & Rollback

## When to use

- A model promotion increases error rate or latency.
- Canary shows statistically significant degradation.
- You need a fast, repeatable rollback with clear ownership.

## Preconditions (should already be true)

- Release metadata includes immutable image digests and artifact checksums.
- Canary percentage and rollback strategy are defined.
- Approval gate exists for promotion to production.

## Steps

1) **Freeze promotion**
   - Stop further rollouts; confirm the current serving version and traffic split.

2) **Validate provenance**
   - Confirm `data_sha256` and `model_sha256` match the promoted artifacts.
   - Confirm images use immutable `@sha256:` digests.

3) **Rollback**
   - Shift traffic back to the last-known-good version (100%).
   - Keep the failing version available for postmortem reproduction (no deletion yet).

4) **Triage**
   - Compare feature distributions and key metrics between baseline and canary.
   - Correlate errors with trace IDs and request attributes.

5) **Post-incident hardening**
   - Add/strengthen a pre-promotion checklist and automate the validation gates.

