"""Run safe maintenance diagnostics and write a remediation report.

This task can detect missing configuration, but GitHub does not expose secret values
to workflows or permit a workflow to repair a missing secret automatically.
"""
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "troubleshooting_report.md"


def present(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def main() -> int:
    checks = [
        ("OPENAI_API_KEY", present("OPENAI_API_KEY"), "Add/recreate this as an Environment secret in Settings > Environments > facebook-production."),
        ("FB_PAGE_ACCESS_TOKEN", present("FB_PAGE_ACCESS_TOKEN"), "Add a valid Page access token as an Environment secret before enabling publishing."),
        ("EXPECTED_FB_PAGE_ID", present("EXPECTED_FB_PAGE_ID"), "Set the repository/environment variable to the intended Page ID."),
        ("OPENAI_MODEL", present("OPENAI_MODEL"), "Optional: set the model variable; otherwise the Python default is used."),
    ]
    auto_publish = os.getenv("AUTO_PUBLISH", "false").strip().lower() == "true"
    hash_present = present("APPROVED_CONTENT_SHA256")
    approved_file = ROOT / "content" / "approved_caption.txt"
    approved_exists = approved_file.is_file()

    lines = [
        "# CHILD & HOPE Pipeline Troubleshooting Report",
        "",
        f"- Generated (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- Trigger: {os.getenv('GITHUB_EVENT_NAME', 'local/manual')}",
        f"- Publishing mode: {'ENABLED (approval gates still required)' if auto_publish else 'DISABLED — draft-only'}",
        "",
        "## Configuration checks",
        "",
        "| Setting | Status |",
        "|---|---|",
    ]
    for name, ok, _ in checks:
        lines.append(f"| {name} | {'PRESENT' if ok else 'MISSING'} |")
    lines.extend([
        f"| APPROVED_CONTENT_SHA256 | {'PRESENT' if hash_present else 'MISSING'} |",
        f"| content/approved_caption.txt | {'PRESENT' if approved_exists else 'MISSING'} |",
        "",
        "## Remediation tasks",
        "",
    ])

    missing = [(name, fix) for name, ok, fix in checks if not ok and name != "OPENAI_MODEL"]
    if not hash_present:
        missing.append(("APPROVED_CONTENT_SHA256", "Only needed for publishing: set it to the SHA-256 of the exact reviewed caption."))
    if not approved_exists:
        missing.append(("content/approved_caption.txt", "Only needed for publishing: add the exact human-reviewed caption to the repository."))
    if not auto_publish:
        lines.append("- Publishing is intentionally disabled. Keep it disabled until the Page identity, caption approval, and all secrets are verified.")
    if missing:
        for name, fix in missing:
            lines.append(f"- **{name}:** {fix}")
    else:
        lines.append("- No missing required configuration was detected by this diagnostic.")
    lines.extend([
        "",
        "## Safe limits",
        "",
        "- This report never includes secret values.",
        "- A workflow cannot read back, create, or repair a missing GitHub secret. A repository administrator must set it in GitHub Settings.",
        "- The pipeline must stop before any Facebook post when required configuration or approval checks fail.",
        "- This report is diagnostic guidance, not proof that an external API token is valid; API identity checks occur only in the publishing path.",
        "",
    ])
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("=== Maintenance / troubleshooting task ===")
    for name, ok, _ in checks:
        print(f"{name}: {'PRESENT' if ok else 'MISSING'}")
    print(f"Publishing mode: {'ENABLED' if auto_publish else 'DISABLED (draft-only)'}")
    print(f"Troubleshooting report written: {REPORT.name}")
    if missing:
        print(f"Remediation items identified: {len(missing)}. See the uploaded troubleshooting report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
