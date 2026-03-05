from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from portfolio_proof.engine import generate_report, run_validations


class SmokeTests(unittest.TestCase):
    def test_validate_examples_pass(self) -> None:
        result = run_validations(examples_dir=Path("examples"), config_path=Path("examples/project.toml"))
        self.assertFalse(result.failed(strict=False), msg=result.to_text())

    def test_report_is_generated_and_has_key_sections(self) -> None:
        result = run_validations(examples_dir=Path("examples"), config_path=Path("examples/project.toml"))
        report = generate_report(result)
        self.assertIn("# Portfolio Proof Report", report)
        self.assertIn("## Pain points → what this repo demonstrates", report)
        self.assertIn("ML/AI platform operationalization", report)
        self.assertIn("Infrastructure drift", report)
        self.assertIn("Low-signal observability", report)

    def test_strict_mode_fails_when_service_missing_required_metric(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            shutil.copytree(Path("examples"), tmp / "examples")
            shutil.copytree(Path("docs"), tmp / "docs")

            service_cfg = tmp / "examples" / "observability" / "service.toml"
            text = service_cfg.read_text(encoding="utf-8")
            service_cfg.write_text(
                text.replace(
                    'metrics = ["latency_p95", "error_rate", "throughput"]',
                    'metrics = ["latency_p95", "error_rate"]',
                ),
                encoding="utf-8",
            )

            old_cwd = Path.cwd()
            try:
                os.chdir(tmp)
                result = run_validations(
                    examples_dir=Path("examples"), config_path=Path("examples/project.toml")
                )
                self.assertTrue(result.failed(strict=True), msg=result.to_text())
            finally:
                os.chdir(old_cwd)
