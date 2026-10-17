"""Publish a reviewed research-poster artifact to the configured Facebook Page."""
from __future__ import annotations
import hashlib, os, sys
from datetime import datetime, timezone
from pathlib import Path
import requests

GRAPH_VERSION = os.getenv("FB_GRAPH_VERSION", "v23.0")
PAGE_ID = os.getenv("EXPECTED_FB_PAGE_ID", "1345909531941708").strip()
TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
ROOT = Path(__file__).resolve().parents[1]
POSTER = ROOT / "downloaded-artifact" / "child_hope_research_poster.png"
CAPTION_FILE = ROOT / "downloaded-artifact" / "poster_caption.txt"
REPORT = ROOT / "facebook_research_poster_receipt.md"

def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def main():
    if not TOKEN:
        raise RuntimeError("FB_PAGE_ACCESS_TOKEN is missing.")
    if not POSTER.is_file() or not CAPTION_FILE.is_file():
        raise RuntimeError("Expected poster artifact or caption is missing.")
    caption = CAPTION_FILE.read_text(encoding="utf-8").strip()
    if len(caption) < 30:
        raise RuntimeError("Caption is empty or unexpectedly short.")
    identity = requests.get(
        f"https://graph.facebook.com/{GRAPH_VERSION}/me",
        params={"fields": "id,name", "access_token": TOKEN}, timeout=30)
    identity.raise_for_status()
    page = identity.json()
    if str(page.get("id", "")).strip() != PAGE_ID:
        raise RuntimeError(f"Facebook Page identity mismatch: expected {PAGE_ID}, received {page.get('id')!r}. Refusing to publish.")
    with POSTER.open("rb") as image_file:
        response = requests.post(
            f"https://graph.facebook.com/{GRAPH_VERSION}/{PAGE_ID}/photos",
            data={"caption": caption, "published": "true", "access_token": TOKEN},
            files={"source": ("child_hope_research_poster.png", image_file, "image/png")},
            timeout=90)
    if not response.ok:
        raise RuntimeError(f"Meta photo publish failed: HTTP {response.status_code}: {response.text[:800]}")
    result = response.json()
    post_id = result.get("post_id") or result.get("id")
    if not post_id:
        raise RuntimeError(f"Meta response did not include a photo/post ID: {result}")
    permalink = ""
    try:
        verified = requests.get(
            f"https://graph.facebook.com/{GRAPH_VERSION}/{post_id}",
            params={"fields": "id,permalink_url", "access_token": TOKEN}, timeout=30)
        if verified.ok:
            data = verified.json()
            if str(data.get("id", "")) == str(post_id):
                permalink = str(data.get("permalink_url", "") or "")
    except requests.RequestException:
        pass
    poster_hash = sha256_file(POSTER)
    caption_hash = hashlib.sha256(caption.encode("utf-8")).hexdigest()
    REPORT.write_text("\n".join([
        "# CHILD & HOPE — Research Poster Publication Receipt", "",
        "- Status: PUBLISHED (Meta returned a photo/post ID)",
        f"- Generated (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- Page: {page.get('name', 'configured Page')}", f"- Page ID: {PAGE_ID}",
        f"- Post/photo ID: {post_id}", f"- Poster SHA-256: {poster_hash}",
        f"- Caption SHA-256: {caption_hash}",
        f"- Permalink: {permalink or 'Meta did not return a permalink; locate the post using the ID.'}", "",
        "Publication was initiated manually after a reviewer inspected the research poster artifact.", ""]),
        encoding="utf-8")
    print(f"Published research poster to {page.get('name', 'configured Page')}; post ID: {post_id}")
    print(f"Permalink: {permalink or 'not returned by Meta'}")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
