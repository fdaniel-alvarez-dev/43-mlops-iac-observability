# Runbook: IaC Drift Detection & Response

## When to use

- Prod differs from dev/staging in unexpected ways.
- A change “worked in dev” but fails in prod.
- Manual edits are suspected.

## Steps

1) **Identify the drift**
   - Compare environment inventories and highlight mismatched resources/fields.
   - Confirm whether the difference is intentional (documented) or accidental.

2) **Stop the bleeding**
   - Block further manual changes; require PR-based IaC changes.
   - Pin versions (Terraform + providers) to avoid implicit behavior changes.

3) **Reconcile**
   - Decide target state (prod-as-source vs desired-from-code).
   - Apply the minimal change set with review and change window if needed.

4) **Prevent recurrence**
   - Add a “drift check” job and require it before promotion.
   - Enforce “no latest tags” for images/modules and lock provider versions.

