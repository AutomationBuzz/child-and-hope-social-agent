# CHILD & HOPE Agentic Facebook Workflow

One GitHub Actions entry point coordinates configuration diagnostics, live OpenAI/Meta credential checks, publishing preflight, caption generation, and the existing guarded Facebook publishing step.

## One-time secure setup

In GitHub **Settings → Environments → facebook-production**, add Environment secrets:
- `OPENAI_API_KEY`
- `FB_PAGE_ACCESS_TOKEN` (a Facebook **Page** access token)

Add environment variables:
- `EXPECTED_FB_PAGE_ID=61595341701921`
- `OPENAI_MODEL=gpt-4.1-mini` (optional)
- `AUTO_PUBLISH=false` initially
- `APPROVED_CONTENT_SHA256` only when configuring a reviewed caption for publication

Never paste secrets into chat, source files, workflow YAML, or logs. Agents can verify configured credentials but cannot retrieve private keys from OpenAI or Meta or create GitHub Environment secrets on your behalf.

## Run the workflow

1. Open **Actions → CHILD & HOPE Agentic Facebook Workflow → Run workflow**.
2. The orchestrator runs diagnostics, checks OpenAI and Facebook credentials/Page identity, validates publication safeguards, then creates a draft or attempts guarded publication.
3. Download the `child-and-hope-agentic-run-report` artifact. Start with `orchestrator_report.md`; use the setup/troubleshooting reports for exact remediation.

## Publishing safety

- Default mode is draft-only: `AUTO_PUBLISH=false`.
- To publish, set `AUTO_PUBLISH=true` only after the Page identity is verified and the exact reviewed caption is stored in `content/approved_caption.txt`, with `APPROVED_CONTENT_SHA256` set to its SHA-256.
- The publishing code refuses a missing/mismatched approval hash or Page ID and checks the Facebook API response for a post ID.
- The current duplicate ledger is runner-local and is not reliable across fresh GitHub-hosted runners. Do not rely on it as a durable duplicate-post guarantee; add persistent storage before unattended recurring publishing.
- The scheduled trigger runs daily at 14:00 UTC. Keep publishing disabled until the first manual test succeeds.

## Scope

One text post per run. Image uploads, comments, analytics, and multiple-page publishing are not enabled.
