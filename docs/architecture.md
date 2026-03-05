# Architecture

This repository is a runnable portfolio demonstration that produces an operator-friendly report from a small set of sanitized inputs.

## Data flow

1) **Inputs** (`examples/`)
   - `examples/project.toml`: release metadata + guardrails configuration (single entrypoint).
   - `examples/iac/env_dev.json` and `examples/iac/env_prod.json`: intentionally simple “inventory” snapshots used to highlight drift.
   - `examples/observability/service.toml`: OpenTelemetry + signals expectations.

2) **Checks** (`src/portfolio_proof/`)
   - ML platform operationalization: reproducibility and safe promotion gates.
   - IaC automation: pinned versions, drift signals across environments, and “reviewable change” indicators.
   - Observability: minimum viable signals, correlation expectations, and runbook linkage.
   - Secrets guardrails: deny obvious secret patterns in inputs.

3) **Outputs** (`artifacts/`)
   - `artifacts/report.md`: a human-readable report with:
     - Risks found
     - Recommended guardrails + runbook steps
     - Validation results and environment-drift summary

4) **Runbooks** (`docs/runbooks/`)
   - Playbooks tied to the three pain points: release rollback, IaC drift response, and observability triage.

## Threat model notes (portfolio-level)

- **Asset**: configuration and release metadata (not real production secrets).
- **Primary risks**:
  - Accidental secret leakage via config files or state artifacts.
  - Unreviewable changes (manual edits, “latest” tags) leading to drift and outages.
  - Incident response delay due to missing correlation between logs, traces, and metrics.
- **Controls demonstrated**:
  - `.gitignore` guardrails for `.env*`, keys, tfstate.
  - Deterministic validations that fail fast on “must-have” controls.
  - Runbook links embedded directly in the generated report.

