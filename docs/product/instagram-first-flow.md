# Instagram-First Onboarding Flow

The platform is designed around an Instagram account as the primary brand anchor.

---

## Onboarding Steps

### Step 1 — Identity (`/onboarding`, step 1)
Fields:
- **Brand name** (required)
- **Instagram handle** — accepts `@yourbrand` or `yourbrand`, normalizes on input
- **Website URL** — optional, enables SEO/GEO analysis
- **Description** — optional, used for content generation context

Instagram URL acceptance:
- `https://instagram.com/yourbrand` → extracts `yourbrand`
- `https://www.instagram.com/yourbrand/` → extracts `yourbrand`
- `@yourbrand` → strips `@`, stores `yourbrand`
- `yourbrand` → stored as-is

### Step 2 — Business Context (step 2)
- **Category** — grid of 12 options, drives niche inference
- **Target audience** — free text, used in audience segment personalization

### Step 3 — Goals (step 3)
- **Primary goal** — radio select (6 options)
- **Geography** — chip select (7 regions)

### Step 4 — Confirmation (step 4)
Shows what was generated:
- Trend feed calibrated to your niche
- Audience segment profiles
- Top 6 growth recommendations
- GEO/SEO signals
- Content opportunity themes

---

## What Happens After Onboarding

1. `POST /api/v1/brand/profile` saves the BrandProfile
2. Niche is inferred from category via keyword matching
3. All intelligence modules load niche-specific, brand-personalized data
4. Dashboard overview shows real KPIs from the intelligence engine
5. User is redirected to `/dashboard`

---

## What the Platform Does NOT Do

- It does NOT access Instagram's API without explicit OAuth configuration
- It does NOT automatically post, comment, or interact with accounts
- It does NOT scrape Instagram followers or engagement data
- Growth recommendations are **strategic guidance**, not automated execution

The platform generates intelligence based on your declared brand profile. Real data from Instagram (follower counts, engagement rates, post performance) can be added manually or via future official API integrations.

---

## Honest Capability Statement

This platform:
- **Understands** your brand niche, positioning, and goals
- **Identifies** trending topics relevant to your niche
- **Profiles** your likely audience segments
- **Recommends** content directions and growth actions
- **Supports** a compliant approval workflow before any execution
- **Analyzes** your website for SEO and AI discoverability (if URL provided)

It does NOT guarantee follower growth, traffic increases, or revenue outcomes.
Growth results depend on content quality, consistency, and execution.

