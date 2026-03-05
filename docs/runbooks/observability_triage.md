# Runbook: Observability Triage (Metrics/Logs/Traces)

## Goal

Answer “what broke?” quickly and produce a next action in minutes, not hours.

## Steps

1) **Start from symptoms**
   - Pick one: latency, error rate, throughput, saturation.

2) **Use correlation**
   - Find a representative failing request.
   - Follow the trace, then pivot to logs for the same trace/request ID.

3) **Confirm impact**
   - Check SLO burn rate and error budget.
   - Identify if impact is localized (one endpoint/tenant) or systemic.

4) **Mitigate**
   - Roll back the most recent risky change (release/IaC/config).
   - If mitigations are not obvious, reduce blast radius (traffic shaping, feature flags).

5) **Document**
   - Record the timeline, the signal that led to root cause, and missing signals to add.

