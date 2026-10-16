"""Pipeline agent: maintenance diagnostics, preflight, then content workflow.

Diagnostics run first on every trigger and write troubleshooting_report.md.
Secret values are never printed. Missing credentials cannot be repaired by code;
the workflow reports the exact GitHub setting that needs administrator action.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_step(label: str, command: list[str]) -> None:
    print(f"\n=== Pipeline Agent: {label} ===", flush=True)
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> int:
    print("CHILD & HOPE Pipeline Agent starting.", flush=True)
    print(f"Trigger: {os.getenv('GITHUB_EVENT_NAME', 'local/manual')}", flush=True)
    run_step("maintenance / troubleshooting diagnostics", [sys.executable, "src/troubleshoot.py"])
    run_step("configuration preflight", [sys.executable, "src/validate_config.py"])
    run_step("generate draft / publish only through existing safety gates", [sys.executable, "src/agent.py"])
    print("\nPipeline Agent completed successfully.", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"PIPELINE AGENT ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
