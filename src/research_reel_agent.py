"""Create a vertical educational Facebook Reel from a recent PubMed childhood-cancer research record.

This produces a silent MP4 draft plus a caption and hashtags. It does not publish,
collect personal data, or contact patients/families.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

from research_poster_agent import choose_and_summarize, pubmed_search

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts"
OUT.mkdir(exist_ok=True)
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
WIDTH, HEIGHT, FPS = 1080, 1920, 24
NAVY = (25, 45, 72)
GOLD = (242, 190, 76)
PAPER = (250, 249, 245)
INK = (43, 53, 66)
MUTED = (93, 105, 119)


def font(size: int, bold: bool = False):
    path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if Path(path).exists():
        return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def wrap_lines(draw, text, use_font, max_width):
    lines, current = [], ""
    for word in text.split():
        candidate = (current + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=use_font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def centered_block(draw, text, y, use_font, fill, max_width=900, gap=20, max_lines=5):
    lines = wrap_lines(draw, text, use_font, max_width)[:max_lines]
    for line in lines:
        box = draw.textbbox((0, 0), line, font=use_font)
        x = (WIDTH - (box[2] - box[0])) // 2
        draw.text((x, y), line, font=use_font, fill=fill)
        y += (box[3] - box[1]) + gap
    return y


def make_slide(kicker: str, headline: str, body: str, index: int, total: int) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 310), fill=NAVY)
    draw.rectangle((0, 300, WIDTH, 316), fill=GOLD)
    draw.text((72, 70), "CHILD & HOPE", font=font(42, True), fill=GOLD)
    draw.text((72, 155), "CHILDHOOD CANCER RESEARCH", font=font(30, True), fill=(255, 255, 255))
    draw.rounded_rectangle((72, 400, 1008, 470), radius=24, fill=GOLD)
    draw.text((100, 416), kicker.upper(), font=font(26, True), fill=NAVY)
    y = centered_block(draw, headline, 560, font(58, True), NAVY, 900, 24, 4)
    y += 60
    centered_block(draw, body, y, font(36), INK, 870, 22, 6)
    draw.rectangle((0, 1730, WIDTH, HEIGHT), fill=(238, 241, 244))
    draw.text((72, 1775), "LEARN • SHARE VERIFIED INFORMATION • SUPPORT FAMILIES", font=font(21, True), fill=NAVY)
    draw.text((72, 1830), f"EDUCATIONAL CONTENT • NOT MEDICAL ADVICE     {index}/{total}", font=font(20), fill=MUTED)
    return image


def create_storyboard(research: dict) -> dict:
    client = OpenAI()
    prompt = {
        "study_title": research["title"],
        "journal": research["journal"],
        "date": research["publication_date"],
        "study_type": research.get("study_type", "Not specified"),
        "key_finding": research["key_finding"],
        "limitation": research["limitation"],
        "source_url": research["source_url"],
    }
    response = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        temperature=0.2,
        messages=[
            {"role": "system", "content": (
                "Create an ethical 5-card vertical social video storyboard for CHILD & HOPE about pediatric cancer research. "
                "Only use supplied study facts; do not imply routine screening is available, promise outcomes, or give medical advice. "
                "Do not sensationalize or exploit children/families. Cards should be concise and accessible. "
                "Return JSON with 'slides' array of exactly 5 objects {kicker, headline, body}; "
                "'caption' under 120 words; 'hashtags' array of 8-12 relevant hashtags; 'cta' one gentle line. "
                "Slide 1 introduces the research question, slide 2 explains the study, slide 3 explains the finding, "
                "slide 4 clearly states the limitation, slide 5 gives a gentle learning/sharing CTA and source. "
                "At least one slide must say this is research, not a validated population screening recommendation. "
                "Keep every slide's headline under 9 words and body under 35 words."
            )},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
    )
    data = json.loads(response.choices[0].message.content or "{}")
    slides = data.get("slides", [])
    if len(slides) != 5:
        raise RuntimeError("Storyboard did not contain exactly five slides.")
    for slide in slides:
        for field in ("kicker", "headline", "body"):
            if not isinstance(slide.get(field), str) or not slide[field].strip():
                raise RuntimeError("Storyboard contains a missing slide field.")
    data["hashtags"] = [tag if tag.startswith("#") else "#" + tag for tag in data.get("hashtags", [])]
    data["source_url"] = research["source_url"]
    data["study_title"] = research["title"]
    data["journal"] = research["journal"]
    data["publication_date"] = research["publication_date"]
    data["pmid"] = research["pmid"]
    data["limitation"] = research["limitation"]
    return data


def render_mp4(storyboard: dict) -> Path:
    frames_per_slide = FPS * 5
    frames = [make_slide(s["kicker"], s["headline"], s["body"], i + 1, 5) for i, s in enumerate(storyboard["slides"])]
    video_path = OUT / "child_hope_early_cancer_research_reel.mp4"
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg, "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-", "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", "22",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video_path),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for frame in frames:
            raw = frame.tobytes()
            for _ in range(frames_per_slide):
                process.stdin.write(raw)
        process.stdin.close()
        stderr = process.stderr.read().decode("utf-8", errors="replace")
        code = process.wait()
        if code != 0:
            raise RuntimeError(f"FFmpeg failed: {stderr[-1200:]}")
    finally:
        if process.poll() is None:
            process.kill()
    return video_path


def main() -> int:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required.")
    records = pubmed_search()
    research = choose_and_summarize(records)
    storyboard = create_storyboard(research)
    video = render_mp4(storyboard)
    tags = " ".join(storyboard.get("hashtags", []))
    caption = (
        f"{storyboard.get('caption', '').strip()}\n\n"
        f"{storyboard.get('cta', 'Learn more and share verified information.')}\n\n"
        f"Study: {research['title']} — {research['journal']} ({research['publication_date']})\n"
        f"Source: {research['source_url']}\n\n{tags}\n"
        "#ChildAndHope"
    )
    (OUT / "reel_caption_hashtags.txt").write_text(caption, encoding="utf-8")
    (OUT / "reel_storyboard.json").write_text(json.dumps(storyboard, indent=2, ensure_ascii=False), encoding="utf-8")
    report = [
        "# CHILD & HOPE — Reel Draft Review",
        "",
        f"- Generated UTC: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "- Status: DRAFT — not published",
        f"- Source: {research['source_url']}",
        f"- Study: {research['title']}",
        f"- Journal/date: {research['journal']} / {research['publication_date']}",
        f"- Limitation: {research['limitation']}",
        "- Format: vertical 1080×1920, silent MP4, approximately 25 seconds",
        "",
        "## Review before publishing",
        "- [ ] Verify all claims against the linked article.",
        "- [ ] Confirm the limitation is clear and visible.",
        "- [ ] Check captions and on-screen readability.",
        "- [ ] Confirm permission for any third-party images/music (this draft uses neither).",
        "- [ ] Approve the caption and hashtags.",
        "- [ ] Do not collect or solicit children's medical information in comments or forms.",
        "",
    ]
    (OUT / "reel_review_report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"Created Reel draft: {video}")
    print("Draft only; no Facebook publishing or lead collection was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
