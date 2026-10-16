"""Preflight checks for CHILD & HOPE GitHub Actions deployment.

Never prints secret values. This script validates what the runner actually receives.
"""
import hashlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPROVED_FILE = ROOT / "content" / "approved_caption.txt"


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> int:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "").strip()
    auto_publish = os.getenv("AUTO_PUBLISH", "false").strip().lower() == "true"

    print(f"OPENAI_API_KEY received by runner: {'YES' if key else 'NO'}")
    print(f"OPENAI_MODEL variable set: {'YES' if model else 'NO (the Python default will be used)'}")
    print(f"AUTO_PUBLISH: {'TRUE' if auto_publish else 'FALSE (safe draft-only mode)'}")

    if not key:
        print(
            "CONFIGURATION ERROR: OPENAI_API_KEY is empty inside the job. "
            "Open Settings > Environments > facebook-production > Environment secrets. "
            "Delete and recreate the secret named exactly OPENAI_API_KEY with a valid key, "
            "then rerun this workflow. Do not put the key in YAML or commit it.",
            file=sys.stderr,
        )
        return 1

    if auto_publish:
        token = os.getenv("FB_PAGE_ACCESS_TOKEN", "").strip()
        page_id = os.getenv("EXPECTED_FB_PAGE_ID", "").strip()
        expected_hash = os.getenv("APPROVED_CONTENT_SHA256", "").strip().lower()
        print(f"FB_PAGE_ACCESS_TOKEN received: {'YES' if token else 'NO'}")
        print(f"EXPECTED_FB_PAGE_ID configured: {'YES' if page_id else 'NO'}")
        print(f"APPROVED_CONTENT_SHA256 configured: {'YES' if expected_hash else 'NO'}")
        if not token or not page_id or not expected_hash:
            print("CONFIGURATION ERROR: Required Facebook publishing settings are missing; publication is blocked.", file=sys.stderr)
            return 1
        if not APPROVED_FILE.is_file():
            print("CONFIGURATION ERROR: content/approved_caption.txt is missing; publication is blocked.", file=sys.stderr)
            return 1
        approved = APPROVED_FILE.read_text(encoding="utf-8").strip()
        if not approved or approved.startswith("#") or sha256(approved) != expected_hash:
            print("CONFIGURATION ERROR: approved caption is empty, a placeholder, or its SHA-256 does not match; publication is blocked.", file=sys.stderr)
            return 1

    print("Preflight passed. No secrets were printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
