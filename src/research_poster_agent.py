"""Research-to-poster agent for CHILD & HOPE.

Uses NCBI PubMed E-utilities (not HTML scraping) to discover recent records,
then creates a source-linked educational poster draft. It never publishes to
Facebook. Human review is required before sharing medical research.
"""
from __future__ import annotations

import json
import os
import textwrap
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts"
OUT.mkdir(exist_ok=True)
BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
USER_AGENT = "CHILD-AND-HOPE-ResearchPosterAgent/1.0 (educational use)"
DAYS_BACK = int(os.getenv("RESEARCH_DAYS_BACK", "30"))
MAX_RECORDS = int(os.getenv("RESEARCH_MAX_RECORDS", "12"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
SEARCH_TERM = (
    '("Childhood Neoplasms"[Mesh] OR childhood cancer[Title/Abstract] '
    'OR pediatric cancer[Title/Abstract] OR paediatric cancer[Title/Abstract]) '
    'AND (early detection[Title/Abstract] OR diagnosis[Title/Abstract] '
    'OR biomarker[Title/Abstract] OR screening[Title/Abstract] '
    'OR diagnostic[Title/Abstract] OR precision medicine[Title/Abstract])'
)


def pubmed_search() -> list[dict]:
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=DAYS_BACK)
    response = requests.get(
        f"{BASE}/esearch.fcgi",
        params={
            "db": "pubmed",
            "term": SEARCH_TERM,
            "datetype": "pdat",
            "mindate": start.strftime("%Y/%m/%d"),
            "maxdate": today.strftime("%Y/%m/%d"),
            "sort": "pub_date",
            "retmax": MAX_RECORDS,
            "retmode": "json",
            "tool": "child_hope_research_poster",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    ids = response.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    time.sleep(0.4)
    article_response = requests.get(
        f"{BASE}/efetch.fcgi",
        params={"db": "pubmed", "id": ",".join(ids), "retmode": "xml"},
        headers={"User-Agent": USER_AGENT},
        timeout=45,
    )
    article_response.raise_for_status()
    root = ET.fromstring(article_response.text)
    records = []
    for article in root.findall(".//PubmedArticle"):
        pmid = (article.findtext(".//PMID") or "").strip()
        title = " ".join("".join(article.find(".//ArticleTitle").itertext()).split()) if article.find(".//ArticleTitle") is not None else ""
        journal = " ".join((article.findtext(".//Journal/Title") or "").split())
        pubdate = article.find(".//JournalIssue/PubDate")
        date_parts = []
        if pubdate is not None:
            for tag in ("Year", "Month", "Day", "MedlineDate"):
                value = pubdate.findtext(tag)
                if value:
                    date_parts.append(value)
        date_text = " ".join(date_parts) or "Date not provided in PubMed record"
        authors = []
        for author in article.findall(".//AuthorList/Author")[:5]:
            name = " ".join(x for x in [author.findtext("ForeName"), author.findtext("LastName")] if x)
            if name:
                authors.append(name)
        abstract_parts = []
        for part in article.findall(".//Abstract/AbstractText"):
            label = part.attrib.get("Label", "")
            value = " ".join("".join(part.itertext()).split())
            if value:
                abstract_parts.append(f"{label}: {value}" if label else value)
        doi = ""
        for ident in article.findall(".//ArticleId"):
            if ident.attrib.get("IdType") == "doi":
                doi = (ident.text or "").strip()
                break
        records.append({
            "pmid": pmid,
            "title": title,
            "journal": journal,
            "date": date_text,
            "authors": authors,
            "abstract": "\n".join(abstract_parts),
            "doi": doi,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
        })
    return [r for r in records if r["title"] and r["abstract"]]


def choose_and_summarize(records: list[dict]) -> dict:
    if not records:
        raise RuntimeError(
            f"No recent PubMed records with abstracts found in the last {DAYS_BACK} days. "
            "Try widening RESEARCH_DAYS_BACK or broadening the search query."
        )
    # Give the model only a small set of recent bibliographic records and abstracts.
    compact = [{
        "pmid": r["pmid"], "title": r["title"], "journal": r["journal"],
        "date": r["date"], "abstract": r["abstract"][:6500], "doi": r["doi"], "url": r["url"]
    } for r in records[:8]]
    client = OpenAI()
    response = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a cautious pediatric cancer research communication editor for CHILD & HOPE. "
                    "Use only facts explicitly supported by the supplied PubMed metadata and abstract. "
                    "Select ONE study suitable for a public educational poster about childhood cancer "
                    "diagnosis, early detection, biomarkers, or pediatric oncology. Prefer human clinical "
                    "research or high-quality reviews; clearly label preclinical/lab research if selected. "
                    "Do not call a finding a screening test, cure, breakthrough, or proven benefit unless "
                    "the abstract supports that exact claim. Do not infer causation from association. "
                    "If the abstract is insufficient, choose another record. Return JSON with keys: "
                    "pmid (string), headline (max 9 words), key_finding (2 sentences max), "
                    "why_it_matters (1 sentence), limitation (1 sentence), study_type (short label), "
                    "caption (100 words max), source_url (exact supplied URL), journal (exact supplied journal), "
                    "publication_date (exact supplied date), title (exact supplied title), doi (exact supplied DOI). "
                    "Make the limitation explicit and avoid personal medical advice. Include no fabricated statistics."
                ),
            },
            {"role": "user", "content": json.dumps(compact, ensure_ascii=False)},
        ],
    )
    data = json.loads(response.choices[0].message.content or "{}")
    chosen = next((r for r in records if r["pmid"] == str(data.get("pmid", ""))), None)
    if not chosen:
        raise RuntimeError("Model selected an article outside the supplied PubMed records.")
    for key, source_key in (("title", "title"), ("journal", "journal"), ("publication_date", "date"), ("source_url", "url"), ("doi", "doi")):
        # Bibliographic metadata must come from PubMed, not generated text.
        data[key] = chosen[source_key]
    data["authors"] = chosen["authors"]
    return data


def load_font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def draw_wrapped(draw, text, x, y, max_width, font, fill, line_gap=10, max_lines=8):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".,;:") + "..."
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += draw.textbbox((0, 0), line, font=font)[3] + line_gap
    return y


def create_poster(data: dict) -> Path:
    width, height = 1080, 1350
    navy = (25, 45, 72)
    gold = (242, 190, 76)
    ink = (43, 53, 66)
    muted = (93, 105, 119)
    paper = (250, 249, 245)
    image = Image.new("RGB", (width, height), paper)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, 260), fill=navy)
    draw.rectangle((0, 248, width, 260), fill=gold)
    draw.text((64, 44), "CHILD & HOPE", font=load_font(34, True), fill=gold)
    draw.text((64, 105), "CHILDHOOD CANCER", font=load_font(44, True), fill=(255, 255, 255))
    draw.text((64, 163), "RESEARCH, EXPLAINED", font=load_font(36, True), fill=(255, 255, 255))

    y = 300
    y = draw_wrapped(draw, data.get("headline", "A closer look at childhood cancer research"), 64, y, 950, load_font(42, True), navy, 12, 2)
    y += 28
    draw.rounded_rectangle((64, y, 1016, y + 12), radius=6, fill=gold)
    y += 42
    draw.text((64, y), "WHAT THE STUDY FOUND", font=load_font(25, True), fill=navy)
    y += 48
    y = draw_wrapped(draw, data.get("key_finding", ""), 64, y, 940, load_font(27), ink, 13, 5)
    y += 22
    draw.text((64, y), "WHY IT MATTERS", font=load_font(25, True), fill=navy)
    y += 44
    y = draw_wrapped(draw, data.get("why_it_matters", ""), 64, y, 940, load_font(25), ink, 11, 3)
    y += 16
    draw.text((64, y), "IMPORTANT LIMITATION", font=load_font(22, True), fill=navy)
    y += 38
    y = draw_wrapped(draw, data.get("limitation", ""), 64, y, 940, load_font(21), muted, 9, 3)

    # Source footer is fixed to preserve citation visibility.
    draw.rectangle((0, 1110, width, height), fill=(238, 241, 244))
    draw.text((64, 1130), "STUDY SNAPSHOT • NOT MEDICAL ADVICE", font=load_font(20, True), fill=navy)
    source_title = data.get("title", "")
    draw_wrapped(draw, source_title, 64, 1170, 950, load_font(16, True), ink, 4, 2)
    source_line = f'{data.get("journal", "")} | {data.get("publication_date", "")} | PMID: {data.get("pmid", "")}'
    draw_wrapped(draw, source_line, 64, 1222, 950, load_font(15), muted, 4, 2)
    draw_wrapped(draw, data.get("source_url", ""), 64, 1265, 950, load_font(15), navy, 4, 2)
    draw.text((64, 1310), "Learn more. Share verified information. Support families.", font=load_font(17, True), fill=navy)

    path = OUT / "child_hope_research_poster.png"
    image.save(path, format="PNG", optimize=True)
    return path


def main() -> int:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required as a GitHub Actions secret.")
    records = pubmed_search()
    data = choose_and_summarize(records)
    poster = create_poster(data)
    caption = (
        f'{data["headline"]}\n\n{data["caption"]}\n\n'
        f'Source: {data["journal"]} ({data["publication_date"]}). '
        f'{data["source_url"]}\n\n'
        "#ChildhoodCancer #ChildAndHope #ResearchLiteracy"
    )
    (OUT / "poster_caption.txt").write_text(caption + "\n", encoding="utf-8")
    summary = [
        "# CHILD & HOPE — Research Poster Review",
        "",
        f'- Generated (UTC): {datetime.now(timezone.utc).isoformat(timespec="seconds")}',
        f"- Search window: last {DAYS_BACK} days",
        f"- PubMed records with abstracts considered: {len(records)}",
        "- Status: DRAFT — human review required; not published to Facebook",
        "",
        f'## {data["title"]}',
        "",
        f'- Journal: {data["journal"]}',
        f'- Publication date: {data["publication_date"]}',
        f'- Study type: {data.get("study_type", "Not specified")}',
        f'- Authors listed by PubMed: {", ".join(data.get("authors", [])) or "See source record"}',
        f'- PMID: {data["pmid"]}',
        f'- DOI: {data.get("doi", "") or "Not listed in PubMed record"}',
        f'- Source: {data["source_url"]}',
        "",
        "## Draft interpretation",
        "",
        f'**Key finding:** {data["key_finding"]}',
        "",
        f'**Why it matters:** {data["why_it_matters"]}',
        "",
        f'**Limitation:** {data["limitation"]}',
        "",
        "## Review checklist",
        "",
        "- [ ] Confirm the poster wording against the linked abstract/full paper.",
        "- [ ] Confirm the study type and limitation are represented accurately.",
        "- [ ] Check text readability and source URL on the image.",
        "- [ ] Approve the caption before any social publication.",
        "- [ ] Do not interpret this educational poster as medical advice.",
        "",
    ]
    (OUT / "research_summary.md").write_text("\n".join(summary), encoding="utf-8")
    print(f"Poster created: {poster}")
    print(f"Records with abstracts considered: {len(records)}")
    print("Draft only. No Facebook API or publishing step was called.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
