"""Pipeline agent: validate configuration, then run the existing content agent.

This orchestrates the pipeline locally in GitHub Actions. It never prints secret values.
Live Facebook publication remains governed by AUTO_PUBLISH and the agent's approval/hash gates.
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
