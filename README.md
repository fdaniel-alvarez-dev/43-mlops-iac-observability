# 43-mlops-iac-observability

Portfolio-grade, runnable proof that tackles three recurring production pain points:

1) ML/AI platform operationalization (repeatable training→serving, reproducible environments, safe releases)
2) Infrastructure drift and fragile automation (reviewable, consistent IaC across environments)
3) Low-signal observability (fast “what broke?” with actionable runbooks)

## Architecture (inputs → checks → outputs → runbooks)

- Inputs: sanitized example configs in `examples/`
- Checks: deterministic, standard-library-only validations (`python -m portfolio_proof validate`)
- Outputs: a human-readable report in `artifacts/report.md`
- Runbooks: operator-ready playbooks in `docs/runbooks/`

See `docs/architecture.md` for the full flow and threat-model notes.

## Quick start

```bash
make setup
make demo
make test-demo
```

Then open `artifacts/report.md`.

## Demo

`make demo` runs:

- `validate`: enforces release/IaC/observability “must-haves” against `examples/`
- `report`: generates `artifacts/report.md` mapping findings to the 3 pain points and to concrete runbooks

Key files used in the demo:

- `examples/project.toml` (single entrypoint config)
- `examples/iac/env_dev.json` + `examples/iac/env_prod.json` (environment inventory used for drift signals)
- `examples/observability/service.toml` (OpenTelemetry + SLO/alerts signals)

## Security

- No secrets: this repo includes a lightweight “secret pattern” scan in the validations and `.gitignore` guardrails.
- Least privilege mindset: demo config is intentionally minimal; real deployments should scope tokens/roles to per-environment and per-pipeline needs.

Full details: `docs/security.md`.

## Intentionally out of scope

- Deploying real infrastructure or a real ML model (this is a deterministic, local portfolio demo).
- Third-party tooling (the runnable parts are standard library only by design).

## Sponsorship and contact

Sponsored by:
CloudForgeLabs  
https://cloudforgelabs.ainextstudios.com/  
support@ainextstudios.com

Built by:
Freddy D. Alvarez  
https://www.linkedin.com/in/freddy-daniel-alvarez/

For job opportunities, contact:
it.freddy.alvarez@gmail.com

## License

Personal, educational, and non-commercial use is free. Commercial use requires paid permission.
See `LICENSE` and `COMMERCIAL_LICENSE.md`.
