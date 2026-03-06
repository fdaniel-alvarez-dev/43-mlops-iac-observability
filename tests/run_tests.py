#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"


def run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd or REPO_ROOT),
        env=os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def fail(message: str, *, output: str | None = None, code: int = 1) -> None:
    print(f"FAIL: {message}")
    if output:
        print(output.rstrip())
    raise SystemExit(code)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON: {path}", output=str(exc))
    return {}


def demo_mode() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    guard_path = ARTIFACTS_DIR / "repo_guardrails.json"
    guard = run([sys.executable, "tools/repo_guardrails.py", "--format", "json", "--out", str(guard_path)])
    if guard.returncode != 0:
        fail("Repo guardrails failed (demo mode must be offline).", output=guard.stdout)

    report = load_json(guard_path)
    if report.get("summary", {}).get("errors", 0) != 0:
        fail("Repo guardrails reported errors.", output=json.dumps(report.get("findings", []), indent=2))

    lint = run(["make", "lint"])
    if lint.returncode != 0:
        fail("Lint failed.", output=lint.stdout)

    test = run(["make", "test"])
    if test.returncode != 0:
        fail("Unit tests failed.", output=test.stdout)

    demo = run(["make", "demo"])
    if demo.returncode != 0:
        fail("Demo failed.", output=demo.stdout)

    report_path = ARTIFACTS_DIR / "report.md"
    if not report_path.exists() or report_path.stat().st_size == 0:
        fail("Expected artifacts/report.md to be created and non-empty.")

    print("OK: demo-mode tests passed (offline).")


def _github_get_repo(owner: str, repo: str, token: str) -> dict:
    url = f"https://api.github.com/repos/{owner}/{repo}"
    req = Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(req, timeout=10) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return json.loads(body)


def production_mode() -> None:
    if os.environ.get("PRODUCTION_TESTS_CONFIRM") != "1":
        fail(
            "Production-mode tests require an explicit opt-in.",
            output=(
                "Set `PRODUCTION_TESTS_CONFIRM=1` and rerun:\n"
                "  TEST_MODE=production PRODUCTION_TESTS_CONFIRM=1 python3 tests/run_tests.py\n"
            ),
            code=2,
        )

    ran_external_integration = False

    gh_token = os.environ.get("GITHUB_TOKEN", "").strip()
    gh_repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    gh_owner = os.environ.get("GITHUB_OWNER", "").strip()
    gh_name = os.environ.get("GITHUB_REPO", "").strip()

    wants_github = bool(gh_repo or gh_owner or gh_name)
    if wants_github and not gh_token:
        fail(
            "GitHub integration is requested but GITHUB_TOKEN is missing.",
            output=(
                "Set the required values and rerun:\n"
                "  export GITHUB_TOKEN='<token>'\n"
                "  export GITHUB_REPOSITORY='owner/repo'  # or set GITHUB_OWNER and GITHUB_REPO\n"
                "  TEST_MODE=production PRODUCTION_TESTS_CONFIRM=1 python3 tests/run_tests.py\n"
            ),
            code=2,
        )

    if wants_github:
        if gh_repo and "/" in gh_repo:
            gh_owner, gh_name = gh_repo.split("/", 1)
        missing = [k for k, v in {"GITHUB_OWNER": gh_owner, "GITHUB_REPO": gh_name}.items() if not v]
        if missing:
            fail(
                "GitHub integration is partially configured.",
                output=(
                    "Set all required values and rerun:\n"
                    "  export GITHUB_TOKEN='<token>'\n"
                    "  export GITHUB_REPOSITORY='owner/repo'  # or set GITHUB_OWNER and GITHUB_REPO\n"
                    "  TEST_MODE=production PRODUCTION_TESTS_CONFIRM=1 python3 tests/run_tests.py\n"
                ),
                code=2,
            )

        try:
            data = _github_get_repo(gh_owner, gh_name, gh_token)
        except Exception as exc:
            fail("GitHub REST API check failed.", output=f"{type(exc).__name__}: {exc}")

        if "allow_forking" not in data:
            fail("GitHub REST API response missing allow_forking field.", output=str(list(data.keys())[:20]))
        ran_external_integration = True

    if not ran_external_integration:
        fail(
            "No external integration checks were executed in production mode.",
            output=(
                "Enable at least one real integration:\n"
                "- Set `GITHUB_REPOSITORY` (or `GITHUB_OWNER` and `GITHUB_REPO`) and `GITHUB_TOKEN`.\n\n"
                "Then rerun:\n"
                "  TEST_MODE=production PRODUCTION_TESTS_CONFIRM=1 python3 tests/run_tests.py\n"
            ),
            code=2,
        )

    print("OK: production-mode tests passed (integrations executed).")


def main() -> None:
    mode = os.environ.get("TEST_MODE", "demo").strip().lower()
    if mode not in {"demo", "production"}:
        fail("Invalid TEST_MODE. Expected 'demo' or 'production'.", code=2)

    if mode == "demo":
        demo_mode()
        return

    production_mode()


if __name__ == "__main__":
    main()
