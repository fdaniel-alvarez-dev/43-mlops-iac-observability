# Security

This repo is a **portfolio demo** and intentionally avoids real credentials, but it still demonstrates guardrails you’d want in production.

## Controls demonstrated

- **No secrets by default**
  - `.gitignore` excludes `.env*`, keys, tfstate, and common credential artifacts.
  - `portfolio_proof validate` includes a simple secret-pattern scan over `examples/`.

- **Auditability & reviewability**
  - Single entrypoint config (`examples/project.toml`) designed to be code-reviewed.
  - Drift signals are computed from environment snapshots to force explicit discussion of divergence.

- **Least privilege mindset**
  - The demo assumes pipeline/service identities exist and are scoped per environment.
  - It emphasizes approval gates and rollback paths for releases.

## Out of scope (by design)

- Real cloud IAM policies, key management, or production token handling.
- Real Terraform state backends or live drift detection against a provider API.
- Full OpenTelemetry pipeline deployment (collector, storage, alerting integration).

