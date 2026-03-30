# Demo Guide — AI CMO OS

A complete walkthrough of the demo experience after initial setup.

## Prerequisites

```bash
docker compose up --build -d
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed_demo.py
```

## Step 1: Sign In

1. Open http://localhost:3000
2. You'll be redirected to `/auth`
3. Credentials are pre-filled: `demo@aicmo.os` / `Demo1234!`
4. Click **Sign In**

## Step 2: Dashboard Overview

The dashboard shows:
- **KPI cards**: Organic sessions (+8.3%), leads (-4.2%), avg position
- **Top Recommendations**: 4 seeded recommendations prioritized by score
- **Pending Approvals**: 1 item awaiting review
- **Recent Reports**: The seeded weekly report
- **AI Visibility teaser**: Link to GEO analysis

> Notice the header: **Autonomy: Level 1 — Draft Only**
> This is the safety-first default. No automated publishing will occur.

## Step 3: Sites

1. Click **Sites** in the sidebar
2. You'll see `example-saas.com` (Acme SaaS) in the list
3. Status is **active** (green)
4. Last crawled shows ~2 hours ago

### Add a New Site (Optional)
1. Click **Add Site**
2. Enter any HTTPS URL
3. Click **Start Onboarding**
4. The system will validate the domain, crawl pages, and run analysis

> In demo mode without `ANTHROPIC_API_KEY`, LLM-powered analysis returns
> placeholder content. Set the API key for real intelligence.

## Step 4: SEO Audit

1. Click **SEO Audit** in the sidebar
2. You'll see 4 demo recommendations:
   - **Critical**: Missing title on /pricing (priority: 91)
   - **High**: Thin content on /features (priority: 69)
   - **High**: Create comparison pages (priority: 77, status: approved)
   - **Medium**: AI citation readiness (priority: 60)
3. Click any recommendation to see the detail panel on the right
4. Notice: impact score, effort score, confidence, proposed action
5. Use the category filter to view by type

## Step 5: AI Visibility

1. Click **AI Visibility** in the sidebar
2. Note the **Experimental** badge
3. Overall score: 42/100 (needs improvement)
4. See signal breakdown: Citation Readiness, FAQ Coverage, etc.
5. Read the experimental disclaimer at the top

## Step 6: Content Pipeline

1. Click **Content** in the sidebar
2. You'll see two seeded assets:
   - Blog post (status: **In Review**) — ready for approval
   - Comparison page (status: **Draft**) — has compliance flags
3. Click **Create Brief** to create a new content brief
4. Fill in topic, type, target keyword
5. The system generates a structured brief

## Step 7: Approval Queue

1. Click **Approvals** in the sidebar
2. See the policy banner: Autonomy Level 1 requires explicit approval
3. 1 pending approval: the seeded blog post
4. Click **Approve** or **Reject**
5. The item moves to "Recently Actioned"

> This is the core safety gate. No AI-generated content can be published
> without explicit human review and approval.

## Step 8: Reports

1. Click **Reports** in the sidebar
2. Select the seeded weekly report
3. View: executive summary, KPI tiles, section breakdown
4. Click **Export MD** (mock — full export requires storage configuration)

## Step 9: Connectors

1. Click **Connectors** in the sidebar
2. See all connectors in mock mode:
   - GA4: returns realistic demo data
   - Search Console: returns realistic demo data
   - Slack: logs to console
3. Configure real credentials via `.env` to connect live systems

## Step 10: Admin / System

1. Click **System** in the sidebar
2. View health checks: API, Database, Workers, Agents
3. Confirm: 138 agents registered, autonomy level 1

## Exploring Further

### API Documentation
Visit http://localhost:8000/docs for the full interactive API reference.

### Temporal UI
Visit http://localhost:8088 to see workflow executions in Temporal.

### Direct API Calls
```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@aicmo.os", "password": "Demo1234!"}'

# List recommendations
TOKEN="your-access-token"
curl http://localhost:8000/api/v1/recommendations?site_id=00000000-0000-0000-0003-000000000001 \
  -H "Authorization: Bearer $TOKEN"
```

## Enabling Real AI

Set `ANTHROPIC_API_KEY` in `.env` and restart:

```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
docker compose restart api worker
```

Now all LLM agents will produce real AI-generated output.

## Known Demo Limitations

- Crawl results are pre-seeded; new crawl triggers run async but UI won't auto-refresh
- Report export downloads require storage configuration
- Social/CMS publishing connectors are stub only
- Temporal workflow visibility in UI requires workflow to complete first
