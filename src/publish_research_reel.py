"""Publish a manually reviewed Reel draft to the configured CHILD & HOPE Facebook Page."""
import os
import sys
import time
from pathlib import Path

import requests

GRAPH_VERSION = os.getenv("FB_GRAPH_VERSION", "v23.0")
PAGE_ID = os.getenv("EXPECTED_FB_PAGE_ID", "1345909531941708").strip()
TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "downloaded-artifact" / "child_hope_early_cancer_research_reel.mp4"
CAPTION = ROOT / "downloaded-artifact" / "reel_caption_hashtags.txt"
REPORT = ROOT / "facebook_reel_publication_receipt.md"


def main():
    if not TOKEN:
        raise RuntimeError("FB_PAGE_ACCESS_TOKEN is missing.")
    if not VIDEO.is_file() or not CAPTION.is_file():
        raise RuntimeError("Reel MP4 or caption artifact is missing.")
    caption = CAPTION.read_text(encoding="utf-8").strip()
    if not caption:
        raise RuntimeError("Caption is empty.")

    base = f"https://graph.facebook.com/{GRAPH_VERSION}"
    identity = requests.get(
        f"{base}/me",
        params={"fields": "id,name", "access_token": TOKEN},
        timeout=30,
    )
    identity.raise_for_status()
    page = identity.json()
    if str(page.get("id", "")).strip() != PAGE_ID:
        raise RuntimeError(
            f"Facebook Page mismatch: expected {PAGE_ID}, got {page.get('id')!r}. Refusing to publish."
        )

    size = VIDEO.stat().st_size
    start = requests.post(
        f"{base}/{PAGE_ID}/video_reels",
        params={"upload_phase": "start", "access_token": TOKEN},
        timeout=30,
    )
    start.raise_for_status()
    started = start.json()
    video_id = started.get("video_id")
    upload_url = started.get("upload_url")
    if not video_id or not upload_url:
        raise RuntimeError(f"Meta did not return video_id/upload_url: {started}")

    with VIDEO.open("rb") as video:
        upload = requests.post(
            upload_url,
            headers={
                "Authorization": f"OAuth {TOKEN}",
                "offset": "0",
                "file_size": str(size),
                "Content-Type": "application/octet-stream",
            },
            data=video,
            timeout=180,
        )
    upload.raise_for_status()

    finish = requests.post(
        f"{base}/{PAGE_ID}/video_reels",
        params={
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": caption,
            "access_token": TOKEN,
        },
        timeout=90,
    )
    finish.raise_for_status()
    result = finish.json()
    if result.get("success") is False:
        raise RuntimeError(f"Meta did not confirm Reel publication: {result}")

    # Best-effort status verification; upload completion can be asynchronous.
    permalink = ""
    status = "Meta accepted the publish request; verify on the Page."
    for _ in range(5):
        check = requests.get(
            f"{base}/{video_id}",
            params={"fields": "id,permalink_url,status", "access_token": TOKEN},
            timeout=30,
        )
        if check.ok:
            data = check.json()
            permalink = str(data.get("permalink_url", "") or "")
            if permalink:
                status = "Meta returned a Reel permalink."
                break
        time.sleep(3)

    REPORT.write_text(
        "\n".join([
            "# CHILD & HOPE — Reel Publication Receipt",
            "",
            f"- Page name: {page.get('name', 'configured Page')}",
            f"- Page ID: {PAGE_ID}",
            f"- Reel video ID: {video_id}",
            f"- Status: {status}",
            f"- Permalink: {permalink or 'Not returned by Meta; check the Page and workflow logs.'}",
            f"- MP4 bytes: {size}",
            "",
            "Publication was initiated only after explicit manual confirmation and reviewer approval.",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"Meta accepted Reel publication request. Video ID: {video_id}")
    print(f"Permalink: {permalink or 'not yet returned'}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
