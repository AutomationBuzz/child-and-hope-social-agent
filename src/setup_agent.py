"""Credential setup agent: verify configured OpenAI and Meta credentials safely.

This agent never retrieves keys from an account, prints token values, or writes
credentials to repository files. Add credentials through GitHub Environment Secrets.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "setup_agent_report.md"
OPENAI_MODELS_URL = "https://api.openai.com/v1/models"
META_ME_URL = "https://graph.facebook.com/v23.0/me"


def main() -> int:
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    page_token = os.getenv("FB_PAGE_ACCESS_TOKEN", "").strip()
    expected_page_id = os.getenv("EXPECTED_FB_PAGE_ID", "").strip()
    results = []
    failures = []

    def record(label, status, detail):
        results.append((label, status, detail))
        print(f"{label}: {status} — {detail}")

    if not openai_key:
        record("OpenAI credential", "MISSING", "Set OPENAI_API_KEY under GitHub Settings > Environments > facebook-production > Environment secrets.")
        failures.append("OpenAI API key is missing.")
    else:
        try:
            response = requests.get(
                OPENAI_MODELS_URL,
                headers={"Authorization": f"Bearer {openai_key}"},
                timeout=20,
            )
            if response.ok:
                record("OpenAI credential", "VALID", "OpenAI authenticated the configured key.")
            elif response.status_code in (401, 403):
                record("OpenAI credential", "INVALID", f"OpenAI returned HTTP {response.status_code}; create/verify a key in the OpenAI API dashboard and update the GitHub secret.")
                failures.append("OpenAI key was rejected.")
            else:
                record("OpenAI credential", "INCONCLUSIVE", f"OpenAI returned HTTP {response.status_code}; inspect service/account access.")
                failures.append("OpenAI validation was inconclusive.")
        except requests.RequestException as exc:
            record("OpenAI credential", "INCONCLUSIVE", f"Network/API request failed ({type(exc).__name__}); retry the workflow.")
            failures.append("OpenAI validation request failed.")

    if not page_token:
        record("Facebook Page token", "MISSING", "Set FB_PAGE_ACCESS_TOKEN as an Environment secret; use a Page access token, not an app token.")
        failures.append("Facebook Page token is missing.")
    else:
        try:
            response = requests.get(
                META_ME_URL,
                params={"fields": "id,name", "access_token": page_token},
                timeout=20,
            )
            payload = response.json() if response.content else {}
            if response.ok and payload.get("id"):
                returned_id = str(payload["id"])
                returned_name = str(payload.get("name", "name unavailable"))
                if expected_page_id and returned_id != expected_page_id:
                    record("Facebook Page identity", "MISMATCH", f"Token identifies {returned_name} (ID {returned_id}), but EXPECTED_FB_PAGE_ID does not match. Publishing must remain disabled.")
                    failures.append("Facebook Page ID mismatch.")
                else:
                    record("Facebook Page identity", "VALID", f"Token identifies {returned_name} (ID {returned_id}).")
            else:
                error = payload.get("error", {})
                code = error.get("code", "unknown")
                record("Facebook Page token", "INVALID", f"Meta rejected the token (error code {code}); generate a valid Page access token.")
                failures.append("Facebook token was rejected.")
        except (requests.RequestException, ValueError) as exc:
            record("Facebook Page token", "INCONCLUSIVE", f"Meta API request failed ({type(exc).__name__}); retry the workflow.")
            failures.append("Facebook validation request failed.")

    lines = [
        "# CHILD & HOPE Setup Agent Report",
        "",
        f"- Generated (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "- Secrets are never written to this report.",
        "",
        "| Check | Status | Result |",
        "|---|---|---|",
    ]
    for label, status, detail in results:
        safe_detail = detail.replace("|", "\\|")
        lines.append(f"| {label} | {status} | {safe_detail} |")
    lines.extend(["", "## Setup guidance", ""])
    if failures:
        lines.extend([
            "- Fix the reported configuration issue(s), then rerun the Setup Agent workflow.",
            "- OpenAI key management: https://platform.openai.com/api-keys",
            "- GitHub environment secrets: https://github.com/AutomationBuzz/child-and-hope-social-agent/settings/environments",
            "- Keep AUTO_PUBLISH set to false until the Page identity and approved caption/hash have been verified.",
        ])
    else:
        lines.append("- Both configured credentials passed these API checks. This does not authorize publishing by itself; caption/hash approval gates still apply.")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report saved to {REPORT.name}; no credential values were displayed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
