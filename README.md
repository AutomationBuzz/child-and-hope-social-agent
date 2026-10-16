# CHILD & HOPE Facebook Content Agent

A GitHub Actions agent that drafts mission-aligned Facebook content with the OpenAI API, validates the configured Meta Page identity, and publishes through Meta Graph API only when an explicit content approval hash matches.

## Safety defaults
- `AUTO_PUBLISH` defaults to `false`; first run creates a draft artifact only.
- Publishing requires `AUTO_PUBLISH=true` **and** `APPROVED_CONTENT_SHA256` to match the exact caption in `content/approved_caption.txt`.
- Page ID must equal `EXPECTED_FB_PAGE_ID`.
- A local publication ledger prevents accidental repeated publication of the same approved caption.
- Never put tokens or API keys in repository files.

## GitHub setup
1. Copy this project into your `DataGango/social-media-agent` repository (or a separate test repository).
2. In **Settings → Environments**, use environment name `facebook-production` and configure these environment secrets:
   - `OPENAI_API_KEY`
   - `FB_PAGE_ACCESS_TOKEN`
3. Add repository/environment variables:
   - `EXPECTED_FB_PAGE_ID=61595341701921`
   - `AUTO_PUBLISH=false` initially
   - `OPENAI_MODEL=gpt-4.1-mini` (or another model available to your API account)
4. Run **Actions → CHILD & HOPE Facebook Agent → Run workflow**. It should create a draft artifact without posting.
5. Review `draft_caption.txt`. If approved, copy the exact caption into `content/approved_caption.txt`, calculate its SHA-256 (`shasum -a 256 content/approved_caption.txt` hashes the file including newline; instead use the command below to hash the exact caption bytes), and set `APPROVED_CONTENT_SHA256` to the hash printed by the workflow's draft step or locally:
   ```bash
   python -c "import hashlib,pathlib; p=pathlib.Path('content/approved_caption.txt').read_text().strip(); print(hashlib.sha256(p.encode()).hexdigest())"
   ```
6. Only after the Page identity check and test draft are correct, set `AUTO_PUBLISH=true` and rerun manually. The run will still generate a fresh draft artifact, but will publish only the exact caption in `content/approved_caption.txt` whose hash matches the protected environment variable. Update the approved caption and hash for each new post. Publishing is a real external action.

## Scheduled posting
The workflow includes a daily schedule, but it will only publish if the explicit publishing gates above pass. Leave `AUTO_PUBLISH=false` until you have tested identity and approval.

## Scope
This starter creates one text post at a time. Image uploads, comments, analytics, and multiple-page publishing are intentionally not enabled by default.
