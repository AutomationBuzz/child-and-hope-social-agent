# CHILD & HOPE Agentic Facebook Workflow

One GitHub Actions entry point coordinates configuration diagnostics, live OpenAI/Meta credential checks, publishing preflight, caption generation, and the existing guarded Facebook publishing step.

## Research-to-poster agent

The separate **CHILD & HOPE - Research to Poster** workflow searches recent PubMed records using the official NCBI E-utilities API, summarizes one suitable study with OpenAI, and creates a PNG educational poster plus a source-linked review report and draft caption.

### Run it

1. Open [Actions → Research to Poster](https://github.com/AutomationBuzz/child-and-hope-social-agent/actions/workflows/research-poster-agent.yml).
2. Select **Run workflow** and run it.
3. Open the completed run and download the `child-hope-research-poster-draft` artifact. It contains:
   - `child_hope_research_poster.png`
   - `research_summary.md` with source, study type, limitations, and a review checklist
   - `poster_caption.txt`
4. Review the cited article and every claim before sharing.

The workflow also runs weekly on Fridays at 14:00 UTC. It considers PubMed records published in the last 30 days by default. It uses the official API rather than scraping journal website HTML. The poster agent does **not** publish to Facebook. It needs the existing `OPENAI_API_KEY` repository or environment secret; it does not need the Facebook Page token. If no suitable recent abstract is found, the run fails rather than inventing research.

## One-time secure setup for Facebook publishing

In GitHub **Settings → Environments → facebook-production**, add Environment secrets:
- `OPENAI_API_KEY`
- `FB_PAGE_ACCESS_TOKEN` (a Facebook **Page** access token)

Add environment variables:
- `EXPECTED_FB_PAGE_ID=1345909531941708`
- `OPENAI_MODEL=gpt-4.1-mini` (optional)
- `AUTO_PUBLISH=false` initially
- `APPROVED_CONTENT_SHA256` only when configuring a reviewed caption for publication

Never paste secrets into chat, source files, workflow YAML, or logs. Agents can verify configured credentials but cannot retrieve private keys from OpenAI or Meta or create GitHub Environment secrets on your behalf.

## Run the Facebook workflow

1. Open **Actions → CHILD & HOPE Agentic Facebook Workflow → Run workflow**.
2. The orchestrator runs diagnostics, checks OpenAI and Facebook credentials/Page identity, validates publishing safeguards, then creates a draft or attempts guarded publication.
3. Download the `child-and-hope-agentic-run-report` artifact. Start with `orchestrator_report.md`; use the setup/troubleshooting reports for remediation.

## Publishing safety

- Keep publishing disabled by default: `AUTO_PUBLISH=false`.
- Publish only after Page identity is verified and the exact reviewed caption is stored in `content/approved_caption.txt`, with `APPROVED_CONTENT_SHA256` set to its SHA-256.
- The publishing code checks the approval hash, Page ID, and Facebook API response for a post ID.
- The duplicate ledger is runner-local and is not a durable duplicate-post guarantee across fresh GitHub-hosted runners. Add persistent storage before unattended recurring publishing.
- The existing Facebook scheduled workflow should remain draft-only until tested.

## CHILD & HOPE content safeguards

- Use compassionate, accurate, non-sensational language.
- Cite the original research and distinguish study findings from established clinical guidance.
- State important limitations and label posters as educational, not medical advice.
- Never invent statistics, patient stories, partnerships, fundraising claims, or medical recommendations.
- Human review is required before a research poster or caption is shared.
