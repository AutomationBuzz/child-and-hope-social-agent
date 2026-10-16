"""Single entry point for the CHILD & HOPE Facebook posting workflow.

Runs diagnostics, live credential/Page validation, publishing preflight, and the
existing draft/publish agent in order. Stops at the first failed gate and always
writes a short status report. Secret values are never intentionally logged.
"""
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "orchestrator_report.md"

STAGES = [
    ("Diagnostics", [sys.executable, "src/troubleshoot.py"]),
    ("Credential and Page identity validation", [sys.executable, "src/setup_agent.py"]),
    ("Publishing safety preflight", [sys.executable, "src/validate_config.py"]),
    ("Create draft / publish approved caption", [sys.executable, "src/agent.py"]),
]


def main() -> int:
    results = []
    failed_stage = None
    print("CHILD & HOPE Agentic Orchestrator started.", flush=True)
    print(f"Trigger: {os.getenv('GITHUB_EVENT_NAME', 'local/manual')}", flush=True)

    for label, command in STAGES:
        print(f"\n=== {label} ===", flush=True)
        completed = subprocess.run(command, cwd=ROOT, check=False)
        if completed.returncode == 0:
            results.append((label, "PASS"))
            continue
        results.append((label, f"FAIL (exit {completed.returncode})"))
        failed_stage = label
        print(f"Stopping safely after failed stage: {label}", file=sys.stderr, flush=True)
        break

    lines = [
        "# CHILD & HOPE Orchestrator Report",
        "",
        f"- Generated (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- Trigger: {os.getenv('GITHUB_EVENT_NAME', 'local/manual')}",
        f"- Publishing mode: {'AUTO_PUBLISH=true' if os.getenv('AUTO_PUBLISH', 'false').lower() == 'true' else 'draft-only'}",
        "",
        "| Stage | Result |",
        "|---|---|",
    ]
    lines.extend(f"| {label} | {status} |" for label, status in results)
    lines.extend(["", "## Outcome", ""])
    if failed_stage:
        lines.append(f"- Workflow stopped safely at **{failed_stage}**. Open the matching setup or troubleshooting report for remediation.")
        lines.append("- No later stage was run after the failure.")
    else:
        lines.append("- All stages completed successfully. Check the uploaded draft and publishing output to confirm the run's outcome.")
    lines.extend([
        "",
        "## Safety",
        "",
        "- Secret values are not written to this report.",
        "- Publishing remains gated by AUTO_PUBLISH, Page identity, approved caption, and matching SHA-256.",
        "- A successful workflow run does not itself prove a post exists unless the publishing stage returned a Facebook post ID.",
        "",
    ])
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Orchestrator report written: {REPORT.name}", flush=True)
    return 1 if failed_stage else 0


if __name__ == "__main__":
    raise SystemExit(main())
