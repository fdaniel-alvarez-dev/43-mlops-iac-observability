#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Finding:
    severity: str  # ERROR | WARN | INFO
    rule_id: str
    message: str
    path: str | None = None


def add(findings: list[Finding], severity: str, rule_id: str, message: str, path: Path | None = None) -> None:
    findings.append(
        Finding(
            severity=severity,
            rule_id=rule_id,
            message=message,
            path=str(path.relative_to(REPO_ROOT)) if path else None,
        )
    )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def summarize(findings: list[Finding]) -> dict:
    return {
        "errors": sum(1 for f in findings if f.severity == "ERROR"),
        "warnings": sum(1 for f in findings if f.severity == "WARN"),
        "info": sum(1 for f in findings if f.severity == "INFO"),
    }


def check_docs_and_license(findings: list[Finding]) -> None:
    for required in ["README.md", "NOTICE.md", "COMMERCIAL_LICENSE.md", "GOVERNANCE.md", "LICENSE"]:
        path = REPO_ROOT / required
        if not path.exists():
            add(findings, "ERROR", "repo.required_file", f"Missing required file: {required}", path)

    lic = REPO_ROOT / "LICENSE"
    if lic.exists():
        text = read_text(lic)
        if "it.freddy.alvarez@gmail.com" not in text:
            add(findings, "ERROR", "license.contact", "LICENSE must include the commercial licensing contact email.", lic)


def check_readme_is_generic(findings: list[Finding]) -> None:
    readme = REPO_ROOT / "README.md"
    if not readme.exists():
        return
    text = read_text(readme)
    if re.search(r"(?i)job-boards\\.greenhouse\\.io|\\bgh_jid\\b", text):
        add(findings, "ERROR", "docs.branding", "README contains job-posting identifiers; keep it generic.", readme)


def check_gitignore(findings: list[Finding]) -> None:
    ignore = REPO_ROOT / ".gitignore"
    if not ignore.exists():
        add(findings, "ERROR", "gitignore.missing", ".gitignore is missing.", ignore)
        return
    text = read_text(ignore)
    required = ["artifacts/", ".[0-9][0-9]_*.txt", "*.pyc"]
    for r in required:
        if r not in text:
            add(findings, "WARN", "gitignore.rule", f"Consider adding gitignore rule: {r}", ignore)


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline repository guardrails.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--out", default="", help="Write output to a file (optional).")
    args = parser.parse_args()

    findings: list[Finding] = []
    check_docs_and_license(findings)
    check_readme_is_generic(findings)
    check_gitignore(findings)

    report = {"summary": summarize(findings), "findings": [asdict(f) for f in findings]}
    if args.format == "json":
        output = json.dumps(report, indent=2, sort_keys=True)
    else:
        lines = []
        for f in findings:
            where = f" ({f.path})" if f.path else ""
            lines.append(f"{f.severity} {f.rule_id}{where}: {f.message}")
        lines.append("")
        lines.append(f"Summary: {report['summary']}")
        output = "\n".join(lines)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    return 1 if report["summary"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
