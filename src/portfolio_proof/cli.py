from __future__ import annotations

import argparse
from pathlib import Path

from .engine import ValidationError, generate_report, run_validations


def _examples_dir(value: str) -> Path:
    p = Path(value)
    if not p.exists() or not p.is_dir():
        raise argparse.ArgumentTypeError(f"examples dir not found: {value}")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="portfolio_proof")
    sub = parser.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--examples", type=_examples_dir, default=Path("examples"))
    common.add_argument(
        "--config",
        type=Path,
        default=Path("examples/project.toml"),
        help="Path to the entrypoint TOML config.",
    )

    p_validate = sub.add_parser("validate", parents=[common], help="Validate example inputs.")
    p_validate.add_argument("--strict", action="store_true", help="Treat warnings as failures.")

    p_report = sub.add_parser("report", parents=[common], help="Generate artifacts/report.md.")
    p_report.add_argument("--out", type=Path, default=Path("artifacts/report.md"))

    sub.add_parser("lint", parents=[common], help="Repo-local lint checks (stdlib only).")

    args = parser.parse_args(argv)

    if args.cmd == "validate":
        try:
            result = run_validations(examples_dir=args.examples, config_path=args.config)
        except ValidationError as exc:
            print(str(exc))
            return 2
        if result.failed(strict=args.strict):
            print(result.to_text())
            return 1
        return 0

    if args.cmd == "report":
        try:
            result = run_validations(examples_dir=args.examples, config_path=args.config)
        except ValidationError as exc:
            print(str(exc))
            return 2
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(generate_report(result), encoding="utf-8")
        print(f"wrote {args.out}")
        return 0

    if args.cmd == "lint":
        try:
            result = run_validations(examples_dir=args.examples, config_path=args.config)
        except ValidationError as exc:
            print(str(exc))
            return 2
        if result.failed(strict=False):
            print(result.to_text())
            return 1
        return 0

    raise AssertionError("unreachable")
