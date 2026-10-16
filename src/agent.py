import hashlib
import json
import os
import sys
from pathlib import Path

import requests
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
MISSION_FILE = ROOT / "content" / "mission.md"
APPROVED_FILE = ROOT / "content" / "approved_caption.txt"
STATE_FILE = ROOT / "state" / "published_hashes.json"
DRAFT_FILE = ROOT / "draft_caption.txt"

GRAPH_VERSION = os.getenv("FB_GRAPH_VERSION", "v23.0")
EXPECTED_PAGE_ID = os.getenv("EXPECTED_FB_PAGE_ID", "61595341701921").strip()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
AUTO_PUBLISH = os.getenv("AUTO_PUBLISH", "false").lower() == "true"
APPROVED_HASH = os.getenv("APPROVED_CONTENT_SHA256", "").strip().lower()


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def create_draft() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")
    mission = MISSION_FILE.read_text(encoding="utf-8")
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=MODEL,
        instructions=(
            "You are the content editor for CHILD & HOPE's Facebook Page. "
            "Write one original, warm, accurate Facebook post in 80-150 words. "
            "Do not invent statistics, names, patient stories, partnerships, donation links, "
            "or claims. Avoid medical advice. If a factual research claim is included, "
            "include a credible source URL in the caption. Output only the caption."
        ),
        input=(
            "Create a useful post for the current day based on these editorial principles. "
            "Choose a fresh angle within the mission; do not claim current news unless sourced.\n\n"
            + mission
        ),
    )
    caption = response.output_text.strip()
    if len(caption) < 30:
        raise RuntimeError("Generated caption is unexpectedly short.")
    return caption


def verify_page(token: str) -> dict:
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/me"
    r = requests.get(url, params={"fields": "id,name", "access_token": token}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if str(data.get("id", "")).strip() != EXPECTED_PAGE_ID:
        raise RuntimeError(
            f"Page identity mismatch: expected {EXPECTED_PAGE_ID}, "
            f"received {data.get('id')!r}. Refusing to publish."
        )
    return data


def publish_caption(token: str, caption: str) -> dict:
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{EXPECTED_PAGE_ID}/feed"
    r = requests.post(
        url,
        data={"message": caption, "access_token": token},
        timeout=45,
    )
    if not r.ok:
        # Avoid printing token-bearing request URLs or secret values.
        raise RuntimeError(f"Meta publish failed: HTTP {r.status_code}: {r.text[:800]}")
    return r.json()


def main() -> None:
    caption = create_draft()
    DRAFT_FILE.write_text(caption + "\n", encoding="utf-8")
    digest = sha256(caption)
    print(f"Draft written to draft_caption.txt; caption SHA-256: {digest}")

    if not AUTO_PUBLISH:
        print("AUTO_PUBLISH is false. Draft-only run; no Facebook post was created.")
        return

    token = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError("FB_PAGE_ACCESS_TOKEN is missing.")

    approved = APPROVED_FILE.read_text(encoding="utf-8").strip()
    if not approved or approved.startswith("#"):
        raise RuntimeError("No reviewed caption found in content/approved_caption.txt.")
    approved_digest = sha256(approved)

    if not APPROVED_HASH or APPROVED_HASH != approved_digest:
        raise RuntimeError("APPROVED_CONTENT_SHA256 mismatch. Refusing to publish.")

    # The model-generated draft is saved for review. Publishing uses only the exact
    # reviewed caption whose SHA-256 is configured in the protected environment.
    caption_to_publish = approved
    digest = approved_digest

    page = verify_page(token)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {"published_hashes": []}
    if digest in state.get("published_hashes", []):
        raise RuntimeError("This exact caption was already published. Refusing duplicate publication.")

    result = publish_caption(token, caption_to_publish)
    post_id = result.get("id")
    if not post_id:
        raise RuntimeError(f"Meta response did not include a post ID: {result}")

    state.setdefault("published_hashes", []).append(digest)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(f"Published successfully to {page.get('name', 'configured Page')}; post ID: {post_id}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
