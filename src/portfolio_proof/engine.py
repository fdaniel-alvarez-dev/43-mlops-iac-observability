from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


class ValidationError(RuntimeError):
    pass


Severity = str  # "error" | "warning" | "info"


@dataclass(frozen=True)
class Finding:
    severity: Severity
    area: str
    title: str
    detail: str


@dataclass(frozen=True)
class ValidationResult:
    config_path: Path
    examples_dir: Path
    findings: tuple[Finding, ...]
    inputs_used: tuple[Path, ...]
    drift_summary: str

    def failed(self, *, strict: bool = False) -> bool:
        if strict:
            return any(f.severity in ("error", "warning") for f in self.findings)
        return any(f.severity == "error" for f in self.findings)

    def counts(self) -> dict[str, int]:
        out = {"error": 0, "warning": 0, "info": 0}
        for f in self.findings:
            out[f.severity] = out.get(f.severity, 0) + 1
        return out

    def to_text(self) -> str:
        c = self.counts()
        lines = [f"errors={c['error']} warnings={c['warning']} info={c['info']}"]
        for f in self.findings:
            lines.append(f"[{f.severity}] {f.area}: {f.title} — {f.detail}")
        return "\n".join(lines)


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"missing config file: {path}") from exc
    except Exception as exc:  # noqa: BLE001 - keep stdlib-only + friendly errors
        raise ValidationError(f"failed to parse TOML: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"invalid TOML root in {path}")
    return data


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"missing json file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid json file: {path}: {exc}") from exc


_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH) PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bASIA[0-9A-Z]{16}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"(?i)\b(password|passwd|secret|api_key|token)\s*=\s*['\"][^'\"]+['\"]"),
)


def _scan_for_secrets(files: Iterable[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in files:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for pat in _SECRET_PATTERNS:
            if pat.search(text):
                findings.append(
                    Finding(
                        severity="error",
                        area="security",
                        title="Secret-like pattern detected",
                        detail=f"Found potential secret material in {path.as_posix()}",
                    )
                )
                break
    return findings


def _is_pinned_version(spec: str) -> bool:
    return spec.strip().startswith("=") and " " not in spec.strip()


def _require(condition: bool, *, area: str, title: str, detail: str) -> Finding | None:
    if condition:
        return None
    return Finding(severity="error", area=area, title=title, detail=detail)


def _warn(condition: bool, *, area: str, title: str, detail: str) -> Finding | None:
    if condition:
        return None
    return Finding(severity="warning", area=area, title=title, detail=detail)


def _as_path(base: Path, raw: Any, *, context: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValidationError(f"expected path string for {context}")
    p = Path(raw)
    return p if p.is_absolute() else (base / p)


def _inventory_index(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    resources = inventory.get("resources")
    if not isinstance(resources, list):
        raise ValidationError("inventory.resources must be a list")
    out: dict[str, dict[str, Any]] = {}
    for item in resources:
        if not isinstance(item, dict) or "id" not in item:
            raise ValidationError("each inventory resource must be an object with an id")
        out[str(item["id"])] = {k: v for k, v in item.items() if k != "id"}
    return out


def _diff_inventories(dev: dict[str, Any], prod: dict[str, Any]) -> tuple[str, list[Finding]]:
    dev_idx = _inventory_index(dev)
    prod_idx = _inventory_index(prod)

    dev_only = sorted(set(dev_idx) - set(prod_idx))
    prod_only = sorted(set(prod_idx) - set(dev_idx))
    common = sorted(set(dev_idx) & set(prod_idx))

    changed: list[str] = []
    for rid in common:
        if dev_idx[rid] != prod_idx[rid]:
            changed.append(rid)

    summary = (
        f"dev_only={len(dev_only)} prod_only={len(prod_only)} changed={len(changed)} "
        f"(changed_ids={', '.join(changed) if changed else 'none'})"
    )

    findings: list[Finding] = []
    if dev_only or prod_only or changed:
        findings.append(
            Finding(
                severity="warning",
                area="iac_automation",
                title="Environment drift signal detected",
                detail=summary,
            )
        )
    return summary, findings


def run_validations(*, examples_dir: Path, config_path: Path) -> ValidationResult:
    repo_root = Path.cwd()
    cfg = _read_toml(config_path)

    ml = cfg.get("ml_platform")
    iac = cfg.get("iac")
    obs = cfg.get("observability")
    if not isinstance(ml, dict) or not isinstance(iac, dict) or not isinstance(obs, dict):
        raise ValidationError("config must include [ml_platform], [iac], and [observability] tables")

    findings: list[Finding] = []
    inputs_used: list[Path] = [config_path]

    # Security guardrails: scan example inputs for secret-like patterns.
    example_files = [p for p in examples_dir.rglob("*") if p.is_file()]
    findings.extend(_scan_for_secrets(example_files))
    inputs_used.extend(sorted(example_files))

    # ML platform operationalization checks.
    training_image = ml.get("training_image")
    inference_image = ml.get("inference_image")
    findings.append(
        _require(
            isinstance(training_image, str) and "@sha256:" in training_image,
            area="ml_platform",
            title="Training image must be immutable",
            detail="Use an image digest (…@sha256:…) for reproducibility.",
        )
    )
    findings.append(
        _require(
            isinstance(inference_image, str) and "@sha256:" in inference_image,
            area="ml_platform",
            title="Inference image must be immutable",
            detail="Use an image digest (…@sha256:…) for reproducibility.",
        )
    )
    findings.append(
        _require(
            isinstance(ml.get("data_sha256"), str) and len(str(ml.get("data_sha256"))) >= 32,
            area="ml_platform",
            title="Dataset checksum required",
            detail="Track immutable dataset hashes to make training-to-serving reproducible.",
        )
    )
    findings.append(
        _require(
            isinstance(ml.get("model_sha256"), str) and len(str(ml.get("model_sha256"))) >= 32,
            area="ml_platform",
            title="Model artifact checksum required",
            detail="Track model artifact hashes for release provenance and rollback.",
        )
    )
    findings.append(
        _require(
            ml.get("approval_required") is True,
            area="ml_platform",
            title="Approval gate required",
            detail="Require explicit approval for promotion to production.",
        )
    )
    findings.append(
        _require(
            ml.get("promotion_strategy") == "canary",
            area="ml_platform",
            title="Canary promotion required",
            detail="Use canary releases to reduce blast radius.",
        )
    )
    canary_percent = ml.get("canary_percent")
    findings.append(
        _require(
            isinstance(canary_percent, int) and 1 <= canary_percent <= 50,
            area="ml_platform",
            title="Canary percentage must be bounded",
            detail="Set canary_percent to an integer between 1 and 50.",
        )
    )
    findings.append(
        _require(
            ml.get("rollback_strategy") in ("instant", "bluegreen"),
            area="ml_platform",
            title="Rollback strategy must be explicit",
            detail="Define a deterministic rollback approach for safe releases.",
        )
    )
    findings.append(
        _warn(
            ml.get("promotion_strategy") == "canary" and obs.get("otel_enabled") is True,
            area="ml_platform",
            title="Release should be observable",
            detail="Canary promotion needs tracing/metrics to validate impact quickly.",
        )
    )

    # IaC automation checks.
    tf_ver = iac.get("terraform_required_version")
    findings.append(
        _require(
            isinstance(tf_ver, str) and _is_pinned_version(tf_ver),
            area="iac_automation",
            title="Terraform version must be pinned",
            detail="Use an exact version constraint like '=1.7.5'.",
        )
    )
    providers = iac.get("providers")
    if not isinstance(providers, dict) or not providers:
        findings.append(
            Finding(
                severity="error",
                area="iac_automation",
                title="Providers must be pinned",
                detail="Set [iac].providers with exact versions (e.g., aws='=5.40.0').",
            )
        )
    else:
        for name, ver in providers.items():
            ok = isinstance(ver, str) and _is_pinned_version(ver) and "latest" not in ver.lower()
            if not ok:
                findings.append(
                    Finding(
                        severity="error",
                        area="iac_automation",
                        title="Provider version must be pinned",
                        detail=f"Provider {name!s} has invalid version spec: {ver!r}",
                    )
                )
    findings.append(
        _require(
            iac.get("state_backend") in ("remote", "s3", "gcs", "azurerm"),
            area="iac_automation",
            title="Remote state backend required",
            detail="Use a remote backend; never commit tfstate to git.",
        )
    )

    inv_dev_path = _as_path(repo_root, iac.get("inventory_dev"), context="iac.inventory_dev")
    inv_prod_path = _as_path(repo_root, iac.get("inventory_prod"), context="iac.inventory_prod")
    inputs_used.extend([inv_dev_path, inv_prod_path])
    inv_dev = _read_json(inv_dev_path)
    inv_prod = _read_json(inv_prod_path)
    if not isinstance(inv_dev, dict) or not isinstance(inv_prod, dict):
        raise ValidationError("inventory json must be objects")
    drift_summary, drift_findings = _diff_inventories(inv_dev, inv_prod)
    findings.extend(drift_findings)

    # Observability checks.
    findings.append(
        _require(
            obs.get("otel_enabled") is True,
            area="observability",
            title="OpenTelemetry must be enabled",
            detail="Enable OpenTelemetry to correlate traces/logs/metrics.",
        )
    )
    ratio = obs.get("traces_sample_ratio")
    findings.append(
        _require(
            isinstance(ratio, (int, float)) and 0.0 < float(ratio) <= 1.0,
            area="observability",
            title="Trace sampling ratio must be valid",
            detail="Set traces_sample_ratio between 0 and 1 (exclusive of 0).",
        )
    )
    required_metrics = obs.get("required_metrics")
    findings.append(
        _require(
            isinstance(required_metrics, list) and all(isinstance(x, str) for x in required_metrics),
            area="observability",
            title="Required metrics list must be defined",
            detail="Define latency/error/throughput (at minimum) for fast triage.",
        )
    )
    findings.append(
        _require(
            obs.get("logs_correlation") is True,
            area="observability",
            title="Log correlation must be enabled",
            detail="Ensure logs include trace/request identifiers for pivoting from traces.",
        )
    )

    runbooks = obs.get("runbooks")
    if not isinstance(runbooks, list) or not runbooks:
        findings.append(
            Finding(
                severity="error",
                area="observability",
                title="Runbooks must be referenced",
                detail="Provide runbook paths in [observability].runbooks to reduce MTTR.",
            )
        )
    else:
        missing = [rb for rb in runbooks if not (repo_root / rb).exists()]
        if missing:
            findings.append(
                Finding(
                    severity="error",
                    area="observability",
                    title="Runbook files missing",
                    detail="Missing: " + ", ".join(missing),
                )
            )

    service_cfg_path = _as_path(
        repo_root, obs.get("service_config"), context="observability.service_config"
    )
    inputs_used.append(service_cfg_path)
    service_cfg = _read_toml(service_cfg_path)
    otel = service_cfg.get("otel")
    signals = service_cfg.get("signals")
    if not isinstance(otel, dict) or not isinstance(signals, dict):
        findings.append(
            Finding(
                severity="error",
                area="observability",
                title="Service observability config invalid",
                detail="examples/observability/service.toml must include [otel] and [signals].",
            )
        )
    else:
        findings.append(
            _require(
                otel.get("enabled") is True and otel.get("exporter") in ("otlp", "console"),
                area="observability",
                title="Service must export telemetry",
                detail="Enable OTLP export (collector) or console for local validation.",
            )
        )
        metrics = signals.get("metrics")
        findings.append(
            _require(
                isinstance(metrics, list) and all(isinstance(m, str) for m in metrics),
                area="observability",
                title="Service must declare metrics",
                detail="Declare service metrics to ensure required signals exist.",
            )
        )
        if isinstance(metrics, list) and isinstance(required_metrics, list):
            missing_metrics = sorted(set(required_metrics) - set(metrics))
            findings.append(
                _require(
                    not missing_metrics,
                    area="observability",
                    title="Service missing required metrics",
                    detail="Missing metrics: " + ", ".join(missing_metrics) if missing_metrics else "",
                )
            )

    # Defensive cleanup: drop Nones produced by helper constructors.
    findings_clean = tuple(f for f in findings if f is not None)

    # Make inputs deterministic and repository-local in the report.
    inputs_rel: list[Path] = []
    for p in inputs_used:
        try:
            inputs_rel.append(p.resolve().relative_to(repo_root.resolve()))
        except Exception:
            inputs_rel.append(p)

    return ValidationResult(
        config_path=config_path,
        examples_dir=examples_dir,
        findings=findings_clean,
        inputs_used=tuple(sorted(set(inputs_rel))),
        drift_summary=drift_summary,
    )


def generate_report(result: ValidationResult) -> str:
    c = result.counts()
    lines: list[str] = []
    lines.append("# Portfolio Proof Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Validation counts: errors={c['error']}, warnings={c['warning']}, info={c['info']}")
    lines.append(f"- IaC drift summary: {result.drift_summary}")
    lines.append("")
    lines.append("## Inputs used")
    for p in result.inputs_used:
        lines.append(f"- `{p.as_posix()}`")
    lines.append("")
    lines.append("## Pain points → what this repo demonstrates")
    lines.append("")
    lines.append("### 1) ML/AI platform operationalization")
    lines.append("- Immutable images + artifact checksums to make training→serving reproducible.")
    lines.append("- Approval + canary + rollback strategy to reduce blast radius.")
    lines.append("- Runbook: `docs/runbooks/ml_release_guardrails.md`")
    lines.append("")
    lines.append("### 2) Infrastructure drift and fragile automation")
    lines.append("- Pinned Terraform/provider versions to reduce surprise behavior changes.")
    lines.append("- Environment inventory diff used as a drift signal.")
    lines.append("- Runbook: `docs/runbooks/iac_drift_response.md`")
    lines.append("")
    lines.append("### 3) Low-signal observability")
    lines.append("- Minimum viable signals (latency/error/throughput) + trace/log correlation.")
    lines.append("- Runbook linkage embedded in config/report to shorten MTTR.")
    lines.append("- Runbook: `docs/runbooks/observability_triage.md`")
    lines.append("")
    lines.append("## Findings")
    if not result.findings:
        lines.append("- No findings.")
        return "\n".join(lines) + "\n"
    for f in result.findings:
        lines.append(f"- **{f.severity.upper()}** `{f.area}`: {f.title} — {f.detail}")
    lines.append("")
    lines.append("## Recommended next steps")
    lines.append("- Automate `portfolio_proof validate` as a required CI gate before promotion.")
    lines.append("- Treat drift findings as signals to document intent (or reconcile to code).")
    lines.append("- Keep runbooks versioned and referenced from service/config defaults.")
    return "\n".join(lines) + "\n"
