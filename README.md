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

The workflow also runs weekly on Fridays at 14:00 UTC. It considers PubMed records published in the last 30 days by default. It uses the official API rather than scraping journal website HTML. The research workflow creates a draft only. It needs the existing `OPENAI_API_KEY` secret; it does not need the Facebook Page token. If no suitable recent abstract is found, the run fails rather than inventing research.

### Publish a reviewed poster to Facebook

1. Run the Research to Poster workflow and download the artifact. Review `research_summary.md`, open the PubMed source, and inspect the poster image and caption.
2. Copy the numeric **run ID** from that completed research workflow run's URL.
3. Open [Actions → Publish Reviewed Research Poster](https://github.com/AutomationBuzz/child-and-hope-social-agent/actions/workflows/publish-research-poster.yml).
4. Click **Run workflow**, enter the research workflow run ID, and choose `yes` only after you have reviewed and approved that exact artifact.
5. Inspect the result and download the `child-hope-research-poster-publication-receipt` artifact. A successful run should include a Facebook post/photo ID and, when available, a permalink.

This separate workflow uses the `FB_PAGE_ACCESS_TOKEN` secret in the `facebook-production` environment and verifies the Page ID before publishing. Do not run the publisher twice for the same research run ID: a durable cross-run duplicate ledger has not yet been implemented. The publishing workflow is manual-only; the weekly research workflow never publishes automatically.

## Research Reel agent

The **CHILD & HOPE - Research Reel Draft** workflow runs manually or weekly on Mondays at 15:00 UTC. It uses recent PubMed research to create a silent vertical 1080×1920 MP4 Reel draft (about 25 seconds), storyboard, source-linked review report, caption, and hashtags.

1. Open [Actions → Research Reel Draft](https://github.com/AutomationBuzz/child-and-hope-social-agent/actions/workflows/research-reel-agent.yml).
2. Click **Run workflow**.
3. Download the `child-hope-research-reel-draft` artifact and review the MP4, `reel_review_report.md`, and `reel_caption_hashtags.txt`.
4. Approve it before any public posting. This workflow creates drafts only; it does not publish to Facebook.

### Ethical reach and lead generation

Use the Reel CTA to invite people to follow the page, share trusted research, or message the official CHILD & HOPE Page for general information. Do not scrape personal profiles, buy contact lists, target people based on inferred illness, or solicit children's medical details. If running campaigns on other Pages, use only Pages you own or are authorized to manage, with each Page's own approved token and explicit destination allowlist. The current Reel workflow does not publish across multiple Pages or collect leads; those integrations require authorized Page IDs/tokens and a clear privacy notice.



### Publish a reviewed research Reel

1. Run [Research Reel Draft](https://github.com/AutomationBuzz/child-and-hope-social-agent/actions/workflows/research-reel-agent.yml) and download the `child-hope-research-reel-draft` artifact.
2. Watch the MP4, check the source article and limitation in `reel_review_report.md`, and review the caption and hashtags in `reel_caption_hashtags.txt`.
3. Copy the numeric run ID from the completed Reel-draft workflow URL.
4. Open [Publish Reviewed Research Reel](https://github.com/AutomationBuzz/child-and-hope-social-agent/actions/workflows/publish-research-reel.yml), click **Run workflow**, enter the run ID, and choose `yes` only after approving the exact Reel.
5. Check the publication receipt and Facebook Page. Do not run the publisher twice for the same run ID; durable cross-run duplicate protection is not yet implemented.

The Reel publisher uses the Page token in the `facebook-production` environment and verifies the expected Page ID before uploading. The current configuration targets only the known CHILD & HOPE Page (`1345909531941708`). To publish on other Pages, each must be explicitly authorized, added to an allowlist, and configured with its own Page ID and Page access token secret; do not reuse a token for a different Page.

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
