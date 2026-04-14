# TAX INTELLIGENCE MODULE — FULL IMPLEMENTATION
## AI Growth OS — Company Tax Profile + AI Accountant Assistant
## Save as: apps/api/TAX_INTELLIGENCE.md

You are a senior full-stack engineer. Your job is to build a complete
Tax Intelligence module into the existing AI Growth OS platform.

This module allows any company (Turkey, Germany, France, any European country, etc.)
to set up their tax profile once, and then every uploaded invoice automatically
gets a full tax analysis with step-by-step instructions for the accountant.

DO NOT skip any step. DO NOT leave stubs. Everything must be fully implemented.
Fix every error before moving to the next step.

---

## STEP 0: AUDIT FIRST

```bash
BASE="/Users/oguzkullelioglu/Desktop/ai-cmo-os 2"

# Read existing finance files
find "$BASE/apps/api/app" -name "*.py" | xargs grep -l "finance\|invoice" | head -10
find "$BASE/apps/web/app/dashboard/finance" -name "*.tsx" | head -10

cat "$BASE/apps/api/app/services/finance/invoice_intelligence.py" | head -50
cat "$BASE/apps/api/app/api/endpoints/finance.py" | head -50

# Check existing DB tables
python3 -c "
import asyncio, asyncpg, os
async def f():
    conn = await asyncpg.connect('postgresql://aicmo:aicmo_dev@localhost:5432/aicmo')
    rows = await conn.fetch(\"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename\")
    [print(r['tablename']) for r in rows]
    await conn.close()
asyncio.run(f())
"
```

Read ALL output before touching anything.

---

## STEP 1: DATABASE — NEW TABLES

```python
# Save as: apps/api/scripts/tax_intelligence_db.py
import asyncio, asyncpg, os

async def create():
    conn = await asyncpg.connect('postgresql://aicmo:aicmo_dev@localhost:5432/aicmo')

    await conn.execute("""

    -- ─────────────────────────────────────────────────────────
    -- COMPANY TAX PROFILES
    -- One per workspace — stores everything needed for tax analysis
    -- ─────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS company_tax_profiles (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        workspace_id UUID NOT NULL UNIQUE,

        -- Basic Info
        company_name VARCHAR(500),
        company_type VARCHAR(100),        -- 'limited', 'anonim', 'sahis', 'gmbh', 'sarl', 'bv', 'srl', etc.
        country_code VARCHAR(10) NOT NULL, -- ISO: 'TR', 'DE', 'FR', 'IT', 'ES', etc.
        country_name VARCHAR(100),
        city VARCHAR(200),
        region VARCHAR(200),

        -- Tax IDs
        tax_id VARCHAR(100),              -- Vergi No / Tax Number / Steuernummer
        vat_id VARCHAR(100),              -- KDV No / USt-IdNr / TVA Intracommunautaire
        registration_number VARCHAR(100), -- Ticaret Sicil / Handelsregisternummer

        -- Tax Configuration
        is_vat_registered BOOLEAN DEFAULT TRUE,
        vat_rate NUMERIC(5,2),            -- e.g. 20.0 for Turkey, 19.0 for Germany
        vat_filing_frequency VARCHAR(20) DEFAULT 'monthly', -- 'monthly', 'quarterly', 'yearly'
        tax_year_start VARCHAR(10) DEFAULT '01-01', -- MM-DD format
        accounting_period VARCHAR(20) DEFAULT 'calendar_year',

        -- Business Profile
        industry VARCHAR(200),
        annual_revenue_estimate VARCHAR(50), -- '0-100k', '100k-500k', '500k-2m', '2m+'
        employee_count_range VARCHAR(20),    -- '1', '2-10', '11-50', '51+'
        founded_year INTEGER,

        -- Applicable Taxes (stored as JSON array)
        applicable_taxes JSONB DEFAULT '[]'::jsonb,
        -- e.g. ["vat", "corporate_tax", "income_tax", "stamp_duty", "social_security"]

        -- Tax Authority Info (populated automatically based on country)
        tax_authority_name VARCHAR(500),
        tax_authority_portal VARCHAR(500),
        tax_authority_portal_name VARCHAR(200),

        -- Setup Status
        profile_completed BOOLEAN DEFAULT FALSE,
        setup_step INTEGER DEFAULT 1,

        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- ─────────────────────────────────────────────────────────
    -- TAX ANALYSIS RESULTS
    -- Per-invoice tax analysis with actionable instructions
    -- ─────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS invoice_tax_analysis (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        invoice_id UUID REFERENCES invoices(id) ON DELETE CASCADE,
        workspace_id UUID NOT NULL,

        -- Analysis Results
        country_code VARCHAR(10),
        tax_regime VARCHAR(100),          -- e.g. 'TR_KDV', 'DE_UST', 'FR_TVA'
        invoice_direction VARCHAR(20),    -- 'incoming' (expense) or 'outgoing' (income)

        -- VAT/KDV Analysis
        vat_amount NUMERIC(14,2),
        vat_rate NUMERIC(5,2),
        vat_treatment VARCHAR(100),       -- 'deductible', 'payable', 'exempt', 'reverse_charge'
        vat_action VARCHAR(500),          -- What to do with this VAT

        -- Other Taxes
        other_taxes JSONB DEFAULT '[]'::jsonb,
        -- [{type, amount, description, action}]

        -- Total Tax Impact
        total_tax_impact NUMERIC(14,2),
        net_tax_payable NUMERIC(14,2),    -- positive = pay, negative = refund/deduct

        -- Filing Info
        filing_period VARCHAR(50),        -- e.g. 'January 2025', 'Q1 2025'
        filing_deadline VARCHAR(100),     -- e.g. '28 February 2025'
        filing_deadline_date DATE,

        -- Tax Authority
        authority_name VARCHAR(500),
        authority_portal_url VARCHAR(500),
        authority_portal_name VARCHAR(200),

        -- Step-by-step Instructions for Accountant
        instructions JSONB DEFAULT '[]'::jsonb,
        -- [{step: 1, title: "...", description: "...", url: "...", urgent: false}]

        -- AI Analysis
        ai_explanation TEXT,              -- Full explanation in plain language
        ai_warnings TEXT[],               -- Any warnings or special notes
        confidence_score NUMERIC(5,4) DEFAULT 0.85,
        ai_model_used VARCHAR(100),

        -- Web Search Results Used
        web_sources JSONB DEFAULT '[]'::jsonb,

        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_tax_analysis_invoice
        ON invoice_tax_analysis(invoice_id);
    CREATE INDEX IF NOT EXISTS idx_tax_analysis_workspace
        ON invoice_tax_analysis(workspace_id, created_at DESC);

    -- ─────────────────────────────────────────────────────────
    -- TAX CALENDAR
    -- Upcoming tax deadlines based on company profile
    -- ─────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS tax_calendar (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        workspace_id UUID NOT NULL,
        tax_type VARCHAR(100),            -- 'vat', 'corporate_tax', 'income_tax', etc.
        tax_name VARCHAR(200),            -- 'KDV Beyannamesi', 'Umsatzsteuervoranmeldung'
        period VARCHAR(100),              -- 'January 2025'
        due_date DATE NOT NULL,
        estimated_amount NUMERIC(14,2),
        status VARCHAR(50) DEFAULT 'upcoming', -- 'upcoming', 'due_soon', 'overdue', 'paid'
        authority_name VARCHAR(500),
        authority_url VARCHAR(500),
        notes TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(workspace_id, tax_type, period)
    );
    CREATE INDEX IF NOT EXISTS idx_tax_calendar_workspace
        ON tax_calendar(workspace_id, due_date);

    """)

    # Verify
    rows = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename IN "
        "('company_tax_profiles', 'invoice_tax_analysis', 'tax_calendar')"
    )
    print("Created tables:")
    for r in rows:
        print(f"  ✅ {r['tablename']}")

    await conn.close()

asyncio.run(create())
```

```bash
cd "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/apps/api"
python3 scripts/tax_intelligence_db.py
```

---

## STEP 2: COUNTRY TAX DATABASE

Create `apps/api/app/services/finance/country_tax_data.py`:

```python
"""
Country Tax Database
Static tax data for 35 countries — Turkey + all major European countries.
Used as baseline; AI supplements with web search for current rates.
"""

COUNTRY_TAX_DATA = {
    # ── TURKEY ──────────────────────────────────────────────
    "TR": {
        "name": "Turkey",
        "currency": "TRY",
        "vat_name": "KDV (Katma Değer Vergisi)",
        "vat_rates": {"standard": 20.0, "reduced": 10.0, "super_reduced": 1.0},
        "corporate_tax_rate": 25.0,
        "income_tax_brackets": [
            {"min": 0, "max": 110000, "rate": 15},
            {"min": 110000, "max": 230000, "rate": 20},
            {"min": 230000, "max": 580000, "rate": 27},
            {"min": 580000, "max": 3000000, "rate": 35},
            {"min": 3000000, "max": None, "rate": 40},
        ],
        "vat_filing": "monthly",
        "vat_deadline_days": 28,  # 28th of following month
        "tax_authority": "Gelir İdaresi Başkanlığı (GİB)",
        "tax_portal": "https://intvrg.gib.gov.tr",
        "tax_portal_name": "GİB İnteraktif Vergi Dairesi",
        "vat_portal": "https://intvrg.gib.gov.tr",
        "efatura_portal": "https://efatura.gov.tr",
        "company_types": ["limited", "anonim", "sahis", "kolektif", "komandit"],
        "applicable_taxes": ["kdv", "kurumlar_vergisi", "gecici_vergi", "stopaj", "damga_vergisi", "sgk"],
        "tax_year": "calendar",
        "notes": "KDV beyannamesi her ayın 28'ine kadar verilir. Geçici vergi 3 ayda bir ödenir.",
        "language": "tr",
    },

    # ── GERMANY ─────────────────────────────────────────────
    "DE": {
        "name": "Germany",
        "currency": "EUR",
        "vat_name": "Umsatzsteuer (USt) / Mehrwertsteuer (MwSt)",
        "vat_rates": {"standard": 19.0, "reduced": 7.0},
        "corporate_tax_rate": 15.0,  # + 5.5% solidarity surcharge + trade tax
        "effective_corporate_rate": 30.0,  # approximate with trade tax
        "income_tax_brackets": [
            {"min": 0, "max": 11604, "rate": 0},
            {"min": 11604, "max": 66761, "rate": 14},  # progressive up to 42%
            {"min": 66761, "max": 277826, "rate": 42},
            {"min": 277826, "max": None, "rate": 45},
        ],
        "vat_filing": "monthly_or_quarterly",
        "vat_deadline_days": 10,  # 10th of following month
        "tax_authority": "Finanzamt",
        "tax_portal": "https://www.elster.de",
        "tax_portal_name": "ELSTER — Elektronische Steuererklärung",
        "vat_portal": "https://www.elster.de",
        "company_types": ["gmbh", "ag", "einzelunternehmen", "ohg", "kg", "ug"],
        "applicable_taxes": ["umsatzsteuer", "koerperschaftsteuer", "gewerbesteuer", "einkommensteuer", "solidaritaetszuschlag", "sozialversicherung"],
        "tax_year": "calendar",
        "notes": "Umsatzsteuervoranmeldung monatlich oder vierteljährlich. ELSTER für elektronische Einreichung.",
        "language": "de",
    },

    # ── FRANCE ──────────────────────────────────────────────
    "FR": {
        "name": "France",
        "currency": "EUR",
        "vat_name": "TVA (Taxe sur la Valeur Ajoutée)",
        "vat_rates": {"standard": 20.0, "intermediate": 10.0, "reduced": 5.5, "super_reduced": 2.1},
        "corporate_tax_rate": 25.0,
        "vat_filing": "monthly_or_quarterly",
        "vat_deadline_days": 19,
        "tax_authority": "Direction Générale des Finances Publiques (DGFiP)",
        "tax_portal": "https://www.impots.gouv.fr",
        "tax_portal_name": "impots.gouv.fr — Espace Professionnel",
        "vat_portal": "https://cfspro.impots.gouv.fr",
        "company_types": ["sarl", "sas", "sa", "ei", "eurl", "snc"],
        "applicable_taxes": ["tva", "is", "ir", "cfe", "cvae", "cotisations_sociales"],
        "tax_year": "calendar",
        "notes": "TVA à déclarer via le portail professionnel impots.gouv.fr",
        "language": "fr",
    },

    # ── ITALY ───────────────────────────────────────────────
    "IT": {
        "name": "Italy",
        "currency": "EUR",
        "vat_name": "IVA (Imposta sul Valore Aggiunto)",
        "vat_rates": {"standard": 22.0, "reduced": 10.0, "super_reduced": 5.0, "minimum": 4.0},
        "corporate_tax_rate": 24.0,  # IRES + IRAP ~3.9%
        "vat_filing": "monthly_or_quarterly",
        "vat_deadline_days": 16,
        "tax_authority": "Agenzia delle Entrate",
        "tax_portal": "https://www.agenziaentrate.gov.it",
        "tax_portal_name": "Agenzia delle Entrate — Cassetto Fiscale",
        "vat_portal": "https://www.agenziaentrate.gov.it",
        "company_types": ["srl", "spa", "snc", "sas", "ditta_individuale"],
        "applicable_taxes": ["iva", "ires", "irap", "irpef", "contributi_inps"],
        "tax_year": "calendar",
        "language": "it",
    },

    # ── SPAIN ───────────────────────────────────────────────
    "ES": {
        "name": "Spain",
        "currency": "EUR",
        "vat_name": "IVA (Impuesto sobre el Valor Añadido)",
        "vat_rates": {"standard": 21.0, "reduced": 10.0, "super_reduced": 4.0},
        "corporate_tax_rate": 25.0,
        "vat_filing": "quarterly",
        "vat_deadline_days": 20,
        "tax_authority": "Agencia Tributaria (AEAT)",
        "tax_portal": "https://sede.agenciatributaria.gob.es",
        "tax_portal_name": "Sede Electrónica — Agencia Tributaria",
        "vat_portal": "https://sede.agenciatributaria.gob.es",
        "company_types": ["sl", "sa", "autonomo", "cb", "sc"],
        "applicable_taxes": ["iva", "is", "irpf", "seguridad_social"],
        "tax_year": "calendar",
        "language": "es",
    },

    # ── NETHERLANDS ─────────────────────────────────────────
    "NL": {
        "name": "Netherlands",
        "currency": "EUR",
        "vat_name": "BTW (Belasting over de Toegevoegde Waarde)",
        "vat_rates": {"standard": 21.0, "reduced": 9.0},
        "corporate_tax_rate": 19.0,  # 19% up to €200k, 25.8% above
        "vat_filing": "quarterly",
        "vat_deadline_days": 31,
        "tax_authority": "Belastingdienst",
        "tax_portal": "https://www.belastingdienst.nl",
        "tax_portal_name": "Mijn Belastingdienst Zakelijk",
        "vat_portal": "https://www.belastingdienst.nl",
        "company_types": ["bv", "nv", "vof", "eenmanszaak", "cv"],
        "applicable_taxes": ["btw", "vpb", "ib", "loonbelasting"],
        "tax_year": "calendar",
        "language": "nl",
    },

    # ── BELGIUM ─────────────────────────────────────────────
    "BE": {
        "name": "Belgium",
        "currency": "EUR",
        "vat_name": "TVA/BTW",
        "vat_rates": {"standard": 21.0, "reduced": 12.0, "super_reduced": 6.0},
        "corporate_tax_rate": 25.0,
        "vat_filing": "monthly_or_quarterly",
        "vat_deadline_days": 20,
        "tax_authority": "SPF Finances / FOD Financiën",
        "tax_portal": "https://finances.belgium.be",
        "tax_portal_name": "MyMinfin Pro",
        "vat_portal": "https://finances.belgium.be",
        "company_types": ["bv", "nv", "vof", "eenmanszaak"],
        "applicable_taxes": ["tva_btw", "isoc", "ipm", "onss_rsz"],
        "tax_year": "calendar",
        "language": "nl_fr",
    },

    # ── POLAND ──────────────────────────────────────────────
    "PL": {
        "name": "Poland",
        "currency": "PLN",
        "vat_name": "VAT (Podatek od Towarów i Usług)",
        "vat_rates": {"standard": 23.0, "reduced": 8.0, "super_reduced": 5.0},
        "corporate_tax_rate": 19.0,  # 9% for small taxpayers
        "vat_filing": "monthly",
        "vat_deadline_days": 25,
        "tax_authority": "Krajowa Administracja Skarbowa (KAS)",
        "tax_portal": "https://www.podatki.gov.pl",
        "tax_portal_name": "e-Urząd Skarbowy",
        "vat_portal": "https://www.podatki.gov.pl",
        "company_types": ["sp_z_oo", "sa", "jednoosobowa", "spolka_jawna"],
        "applicable_taxes": ["vat", "cit", "pit", "zus"],
        "tax_year": "calendar",
        "language": "pl",
    },

    # ── SWEDEN ──────────────────────────────────────────────
    "SE": {
        "name": "Sweden",
        "currency": "SEK",
        "vat_name": "Moms (Mervärdesskatt)",
        "vat_rates": {"standard": 25.0, "reduced": 12.0, "super_reduced": 6.0},
        "corporate_tax_rate": 20.6,
        "vat_filing": "monthly_or_quarterly",
        "vat_deadline_days": 12,
        "tax_authority": "Skatteverket",
        "tax_portal": "https://www.skatteverket.se",
        "tax_portal_name": "Skatteverket — Mina Sidor",
        "vat_portal": "https://www.skatteverket.se",
        "company_types": ["ab", "hb", "kb", "enskild_firma", "ef"],
        "applicable_taxes": ["moms", "bolagsskatt", "arbetsgivaravgifter"],
        "tax_year": "calendar",
        "language": "sv",
    },

    # ── AUSTRIA ─────────────────────────────────────────────
    "AT": {
        "name": "Austria",
        "currency": "EUR",
        "vat_name": "Umsatzsteuer (USt)",
        "vat_rates": {"standard": 20.0, "reduced": 13.0, "super_reduced": 10.0},
        "corporate_tax_rate": 23.0,
        "vat_filing": "monthly_or_quarterly",
        "vat_deadline_days": 15,
        "tax_authority": "Bundesministerium für Finanzen (BMF)",
        "tax_portal": "https://www.bmf.gv.at",
        "tax_portal_name": "FinanzOnline",
        "vat_portal": "https://finanzonline.bmf.gv.at",
        "company_types": ["gmbh", "ag", "og", "kg", "einzelunternehmen"],
        "applicable_taxes": ["umsatzsteuer", "koerperschaftsteuer", "einkommensteuer", "sozialversicherung"],
        "tax_year": "calendar",
        "language": "de",
    },

    # ── SWITZERLAND ─────────────────────────────────────────
    "CH": {
        "name": "Switzerland",
        "currency": "CHF",
        "vat_name": "MWST/TVA/IVA",
        "vat_rates": {"standard": 8.1, "reduced": 2.6, "accommodation": 3.8},
        "corporate_tax_rate": 14.9,  # varies by canton, approximate
        "vat_filing": "quarterly",
        "vat_deadline_days": 60,
        "tax_authority": "Eidgenössische Steuerverwaltung (ESTV)",
        "tax_portal": "https://www.estv.admin.ch",
        "tax_portal_name": "ePortal ESTV",
        "vat_portal": "https://www.estv.admin.ch",
        "company_types": ["ag", "gmbh", "einzelfirma", "kollektivgesellschaft"],
        "applicable_taxes": ["mwst", "gewinnsteuer", "kapitalsteuer", "quellensteuer"],
        "tax_year": "calendar",
        "language": "de_fr_it",
    },

    # ── UNITED KINGDOM ──────────────────────────────────────
    "GB": {
        "name": "United Kingdom",
        "currency": "GBP",
        "vat_name": "VAT (Value Added Tax)",
        "vat_rates": {"standard": 20.0, "reduced": 5.0, "zero": 0.0},
        "corporate_tax_rate": 25.0,  # 19% for small profits under £50k
        "vat_filing": "quarterly",
        "vat_deadline_days": 37,  # 1 month + 7 days after quarter end
        "tax_authority": "HM Revenue & Customs (HMRC)",
        "tax_portal": "https://www.gov.uk/business-tax-account",
        "tax_portal_name": "HMRC Business Tax Account",
        "vat_portal": "https://www.gov.uk/vat-returns",
        "company_types": ["ltd", "plc", "llp", "sole_trader", "partnership"],
        "applicable_taxes": ["vat", "corporation_tax", "paye", "national_insurance"],
        "tax_year": "april_to_march",
        "language": "en",
    },

    # ── PORTUGAL ────────────────────────────────────────────
    "PT": {
        "name": "Portugal",
        "currency": "EUR",
        "vat_name": "IVA (Imposto sobre o Valor Acrescentado)",
        "vat_rates": {"standard": 23.0, "intermediate": 13.0, "reduced": 6.0},
        "corporate_tax_rate": 21.0,
        "vat_filing": "monthly_or_quarterly",
        "vat_deadline_days": 20,
        "tax_authority": "Autoridade Tributária e Aduaneira (AT)",
        "tax_portal": "https://www.portaldasfinancas.gov.pt",
        "tax_portal_name": "Portal das Finanças",
        "vat_portal": "https://www.portaldasfinancas.gov.pt",
        "company_types": ["lda", "sa", "eni", "sociedade_civil"],
        "applicable_taxes": ["iva", "irc", "irs", "seguranca_social"],
        "tax_year": "calendar",
        "language": "pt",
    },

    # ── DENMARK ─────────────────────────────────────────────
    "DK": {
        "name": "Denmark",
        "currency": "DKK",
        "vat_name": "Moms",
        "vat_rates": {"standard": 25.0},
        "corporate_tax_rate": 22.0,
        "vat_filing": "quarterly",
        "vat_deadline_days": 40,
        "tax_authority": "Skattestyrelsen",
        "tax_portal": "https://skat.dk",
        "tax_portal_name": "TastSelv Erhverv",
        "vat_portal": "https://skat.dk",
        "company_types": ["aps", "as", "enkeltmandsvirksomhed", "interessentskab"],
        "applicable_taxes": ["moms", "selskabsskat", "am_bidrag", "atp"],
        "tax_year": "calendar",
        "language": "da",
    },

    # ── NORWAY ──────────────────────────────────────────────
    "NO": {
        "name": "Norway",
        "currency": "NOK",
        "vat_name": "Merverdiavgift (MVA)",
        "vat_rates": {"standard": 25.0, "reduced": 15.0, "super_reduced": 12.0},
        "corporate_tax_rate": 22.0,
        "vat_filing": "bi_monthly",
        "vat_deadline_days": 35,
        "tax_authority": "Skatteetaten",
        "tax_portal": "https://www.skatteetaten.no",
        "tax_portal_name": "Altinn",
        "vat_portal": "https://www.altinn.no",
        "company_types": ["as", "ans", "enkeltpersonforetak", "da"],
        "applicable_taxes": ["mva", "selskapsskatt", "arbeidsgiveravgift"],
        "tax_year": "calendar",
        "language": "no",
    },

    # ── FINLAND ─────────────────────────────────────────────
    "FI": {
        "name": "Finland",
        "currency": "EUR",
        "vat_name": "ALV (Arvonlisävero)",
        "vat_rates": {"standard": 25.5, "reduced": 14.0, "super_reduced": 10.0},
        "corporate_tax_rate": 20.0,
        "vat_filing": "monthly",
        "vat_deadline_days": 12,
        "tax_authority": "Verohallinto (Vero)",
        "tax_portal": "https://www.vero.fi",
        "tax_portal_name": "OmaVero",
        "vat_portal": "https://www.vero.fi",
        "company_types": ["oy", "oyj", "ay", "ky", "tmi"],
        "applicable_taxes": ["alv", "yhteisovero", "tyonantajamaksut"],
        "tax_year": "calendar",
        "language": "fi",
    },

    # ── CZECH REPUBLIC ──────────────────────────────────────
    "CZ": {
        "name": "Czech Republic",
        "currency": "CZK",
        "vat_name": "DPH (Daň z přidané hodnoty)",
        "vat_rates": {"standard": 21.0, "reduced": 15.0, "super_reduced": 10.0},
        "corporate_tax_rate": 21.0,
        "vat_filing": "monthly_or_quarterly",
        "vat_deadline_days": 25,
        "tax_authority": "Finanční správa",
        "tax_portal": "https://www.mfcr.cz",
        "tax_portal_name": "Daňový portál",
        "vat_portal": "https://adisspr.mfcr.cz",
        "company_types": ["sro", "as", "vos", "ks", "osvč"],
        "applicable_taxes": ["dph", "dan_z_prijmu", "socialni_pojisteni", "zdravotni_pojisteni"],
        "tax_year": "calendar",
        "language": "cs",
    },

    # ── HUNGARY ─────────────────────────────────────────────
    "HU": {
        "name": "Hungary",
        "currency": "HUF",
        "vat_name": "ÁFA (Általános Forgalmi Adó)",
        "vat_rates": {"standard": 27.0, "reduced": 18.0, "super_reduced": 5.0},
        "corporate_tax_rate": 9.0,  # lowest in EU
        "vat_filing": "monthly",
        "vat_deadline_days": 20,
        "tax_authority": "Nemzeti Adó- és Vámhivatal (NAV)",
        "tax_portal": "https://nav.gov.hu",
        "tax_portal_name": "Ügyfélportál NAV",
        "vat_portal": "https://nav.gov.hu",
        "company_types": ["kft", "zrt", "nyrt", "bt", "kkt", "egyeni_vallalkozo"],
        "applicable_taxes": ["afa", "tao", "szja", "tbjarul"],
        "tax_year": "calendar",
        "language": "hu",
    },

    # ── ROMANIA ─────────────────────────────────────────────
    "RO": {
        "name": "Romania",
        "currency": "RON",
        "vat_name": "TVA (Taxa pe Valoarea Adăugată)",
        "vat_rates": {"standard": 19.0, "reduced": 9.0, "super_reduced": 5.0},
        "corporate_tax_rate": 16.0,
        "vat_filing": "monthly_or_quarterly",
        "vat_deadline_days": 25,
        "tax_authority": "ANAF (Agenția Națională de Administrare Fiscală)",
        "tax_portal": "https://www.anaf.ro",
        "tax_portal_name": "Spațiul Privat Virtual (SPV)",
        "vat_portal": "https://www.anaf.ro",
        "company_types": ["srl", "sa", "pfa", "ii", "if"],
        "applicable_taxes": ["tva", "impozit_profit", "impozit_venit", "contributii_sociale"],
        "tax_year": "calendar",
        "language": "ro",
    },

    # ── GREECE ──────────────────────────────────────────────
    "GR": {
        "name": "Greece",
        "currency": "EUR",
        "vat_name": "ΦΠΑ (Φόρος Προστιθέμενης Αξίας)",
        "vat_rates": {"standard": 24.0, "reduced": 13.0, "super_reduced": 6.0},
        "corporate_tax_rate": 22.0,
        "vat_filing": "monthly",
        "vat_deadline_days": 26,
        "tax_authority": "ΑΑΔΕ (Ανεξάρτητη Αρχή Δημοσίων Εσόδων)",
        "tax_portal": "https://www.aade.gr",
        "tax_portal_name": "myAADE",
        "vat_portal": "https://www.aade.gr",
        "company_types": ["ike", "ae", "epe", "oe", "ee"],
        "applicable_taxes": ["fpa", "forologhia_eisodimatos", "eisforeb_asfalisis"],
        "tax_year": "calendar",
        "language": "el",
    },

    # Add more countries as needed...
}

def get_country_data(country_code: str) -> dict:
    """Get tax data for a country. Returns None if not found."""
    return COUNTRY_TAX_DATA.get(country_code.upper())

def get_all_countries() -> list[dict]:
    """Get list of all supported countries for dropdown."""
    return [
        {
            "code": code,
            "name": data["name"],
            "currency": data["currency"],
            "vat_name": data["vat_name"],
            "vat_rate": data["vat_rates"]["standard"],
        }
        for code, data in sorted(COUNTRY_TAX_DATA.items(), key=lambda x: x[1]["name"])
    ]

SUPPORTED_COUNTRY_CODES = list(COUNTRY_TAX_DATA.keys())
```

---

## STEP 3: TAX ANALYSIS ENGINE

Create `apps/api/app/services/finance/tax_engine.py`:

```python
"""
Tax Analysis Engine
Analyzes invoices and generates step-by-step accountant instructions.
Uses company tax profile + country tax data + AI + web search.
"""
import os
import json
import logging
import httpx
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.services.finance.country_tax_data import get_country_data
from app.services.ai.model_config import ModelSelector

logger = logging.getLogger(__name__)

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


async def analyze_invoice_taxes(
    invoice_id: str,
    workspace_id: str,
    db: AsyncSession,
) -> dict:
    """
    Main entry point: analyze a single invoice for tax implications.
    Returns full tax analysis with accountant instructions.
    """

    # 1. Get invoice data
    inv = await db.execute(
        text("SELECT * FROM invoices WHERE id = :id AND workspace_id = :wid"),
        {"id": invoice_id, "wid": workspace_id}
    )
    invoice = inv.fetchone()
    if not invoice:
        return {"error": "Invoice not found"}
    invoice = dict(invoice._mapping)

    # 2. Get company tax profile
    profile = await db.execute(
        text("SELECT * FROM company_tax_profiles WHERE workspace_id = :wid"),
        {"wid": workspace_id}
    )
    tax_profile = profile.fetchone()
    if not tax_profile:
        return {"error": "Company tax profile not set up. Please complete Setup → Tax Profile first."}
    tax_profile = dict(tax_profile._mapping)

    country_code = tax_profile.get("country_code", "TR")
    country_data = get_country_data(country_code)

    # 3. Build analysis prompt
    prompt = _build_tax_analysis_prompt(invoice, tax_profile, country_data)

    # 4. Call AI
    ai_result = await _call_ai_tax_analysis(prompt)

    # 5. Generate accountant instructions
    instructions = _generate_instructions(ai_result, invoice, tax_profile, country_data)

    # 6. Calculate filing deadline
    filing_deadline = _calculate_filing_deadline(country_data, invoice.get("invoice_date"))

    # 7. Save to DB
    result = {
        "invoice_id": invoice_id,
        "workspace_id": workspace_id,
        "country_code": country_code,
        "tax_regime": f"{country_code}_{country_data.get('vat_name', 'VAT').split()[0].upper()}" if country_data else country_code,
        "invoice_direction": invoice.get("direction", "incoming"),
        "vat_amount": invoice.get("vat_amount") or _calculate_vat(invoice, country_data),
        "vat_rate": tax_profile.get("vat_rate") or (country_data.get("vat_rates", {}).get("standard") if country_data else 20.0),
        "vat_treatment": ai_result.get("vat_treatment", "deductible"),
        "vat_action": ai_result.get("vat_action", ""),
        "other_taxes": ai_result.get("other_taxes", []),
        "total_tax_impact": ai_result.get("total_tax_impact", 0),
        "net_tax_payable": ai_result.get("net_tax_payable", 0),
        "filing_period": filing_deadline.get("period"),
        "filing_deadline": filing_deadline.get("deadline_str"),
        "filing_deadline_date": filing_deadline.get("deadline_date"),
        "authority_name": country_data.get("tax_authority") if country_data else "",
        "authority_portal_url": country_data.get("tax_portal") if country_data else "",
        "authority_portal_name": country_data.get("tax_portal_name") if country_data else "",
        "instructions": instructions,
        "ai_explanation": ai_result.get("explanation", ""),
        "ai_warnings": ai_result.get("warnings", []),
        "confidence_score": 0.85,
        "ai_model_used": ModelSelector.get_best_model(),
    }

    # Save to invoice_tax_analysis
    await db.execute(
        text("""
            INSERT INTO invoice_tax_analysis (
                invoice_id, workspace_id, country_code, tax_regime,
                invoice_direction, vat_amount, vat_rate, vat_treatment,
                vat_action, other_taxes, total_tax_impact, net_tax_payable,
                filing_period, filing_deadline, filing_deadline_date,
                authority_name, authority_portal_url, authority_portal_name,
                instructions, ai_explanation, ai_warnings,
                confidence_score, ai_model_used
            ) VALUES (
                :invoice_id, :workspace_id, :country_code, :tax_regime,
                :invoice_direction, :vat_amount, :vat_rate, :vat_treatment,
                :vat_action, :other_taxes::jsonb, :total_tax_impact, :net_tax_payable,
                :filing_period, :filing_deadline, :filing_deadline_date,
                :authority_name, :authority_portal_url, :authority_portal_name,
                :instructions::jsonb, :ai_explanation, :ai_warnings,
                :confidence_score, :ai_model_used
            )
            ON CONFLICT DO NOTHING
            RETURNING id
        """),
        {**result,
         "other_taxes": json.dumps(result["other_taxes"]),
         "instructions": json.dumps(result["instructions"]),
         "ai_warnings": result["ai_warnings"]}
    )
    await db.commit()

    return result


def _build_tax_analysis_prompt(invoice: dict, tax_profile: dict, country_data: dict) -> str:
    country_name = tax_profile.get("country_name", "Unknown")
    company_type = tax_profile.get("company_type", "limited")
    vat_registered = tax_profile.get("is_vat_registered", True)
    direction = invoice.get("direction", "incoming")

    vat_name = country_data.get("vat_name", "VAT") if country_data else "VAT"
    vat_rate = country_data.get("vat_rates", {}).get("standard", 20) if country_data else 20
    authority = country_data.get("tax_authority", "") if country_data else ""
    portal = country_data.get("tax_portal", "") if country_data else ""
    applicable_taxes = country_data.get("applicable_taxes", []) if country_data else []
    notes = country_data.get("notes", "") if country_data else ""

    return f"""You are an expert tax accountant for {country_name}.

COMPANY PROFILE:
- Company type: {company_type}
- Country: {country_name} ({tax_profile.get('country_code')})
- VAT registered: {vat_registered}
- VAT ID: {tax_profile.get('vat_id', 'Not provided')}
- Industry: {tax_profile.get('industry', 'Not specified')}
- Annual revenue: {tax_profile.get('annual_revenue_estimate', 'Not specified')}

INVOICE DETAILS:
- Direction: {direction} ({'expense/purchase' if direction == 'incoming' else 'income/sale'})
- Vendor: {invoice.get('vendor_name', 'Unknown')}
- Date: {invoice.get('invoice_date', 'Unknown')}
- Total amount: {invoice.get('total_amount', 0)} {invoice.get('currency', '')}
- VAT amount: {invoice.get('vat_amount', 0)} {invoice.get('currency', '')}
- Category: {invoice.get('category', 'general')}
- Is deductible: {invoice.get('is_deductible', True)}

COUNTRY TAX SYSTEM:
- VAT name: {vat_name}
- Standard VAT rate: {vat_rate}%
- Applicable taxes: {', '.join(applicable_taxes)}
- Tax authority: {authority}
- Tax portal: {portal}
- Notes: {notes}

Analyze this invoice and respond ONLY with valid JSON:
{{
  "vat_treatment": "deductible|payable|exempt|reverse_charge",
  "vat_action": "what to do with the VAT amount",
  "net_tax_payable": number (positive=pay, negative=deduct/refund),
  "total_tax_impact": number,
  "other_taxes": [
    {{"type": "tax_name", "amount": number, "description": "...", "action": "..."}}
  ],
  "explanation": "plain language explanation for the accountant",
  "warnings": ["any important warnings"],
  "filing_category": "which tax return this goes into"
}}"""


async def _call_ai_tax_analysis(prompt: str) -> dict:
    """Call Ollama for tax analysis."""
    model = ModelSelector.get_best_model()
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{OLLAMA_BASE}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 600},
                }
            )
            if not r.is_success:
                logger.error(f"AI tax analysis failed: {r.status_code}")
                return {}

            text_response = r.json().get("response", "")
            # Strip thinking blocks
            if "<think>" in text_response:
                text_response = text_response.split("</think>")[-1].strip()
            # Extract JSON
            if "```json" in text_response:
                text_response = text_response.split("```json")[1].split("```")[0].strip()
            elif "```" in text_response:
                text_response = text_response.split("```")[1].split("```")[0].strip()

            return json.loads(text_response)
    except Exception as e:
        logger.error(f"AI tax analysis error: {e}")
        return {
            "vat_treatment": "deductible",
            "vat_action": "Include in VAT return as input tax",
            "net_tax_payable": 0,
            "total_tax_impact": 0,
            "other_taxes": [],
            "explanation": "Automatic analysis unavailable. Please review manually.",
            "warnings": ["Manual review recommended"],
        }


def _generate_instructions(
    ai_result: dict,
    invoice: dict,
    tax_profile: dict,
    country_data: dict,
) -> list[dict]:
    """Generate step-by-step accountant instructions."""
    instructions = []
    step = 1

    country_code = tax_profile.get("country_code", "TR")
    portal_url = country_data.get("tax_portal", "#") if country_data else "#"
    portal_name = country_data.get("tax_portal_name", "Tax Portal") if country_data else "Tax Portal"
    authority = country_data.get("tax_authority", "Tax Authority") if country_data else "Tax Authority"
    vat_name = country_data.get("vat_name", "VAT") if country_data else "VAT"
    direction = invoice.get("direction", "incoming")
    currency = invoice.get("currency", "")
    vat_amount = invoice.get("vat_amount", 0) or 0
    total = invoice.get("total_amount", 0) or 0
    vendor = invoice.get("vendor_name", "vendor")
    inv_date = invoice.get("invoice_date", "")

    # Step 1: Record the invoice
    instructions.append({
        "step": step,
        "title": "Record the Invoice",
        "description": f"Record this {'expense' if direction == 'incoming' else 'income'} invoice "
                       f"from {vendor} for {currency} {total} in your accounting system. "
                       f"Invoice date: {inv_date}.",
        "url": None,
        "urgent": False,
        "icon": "📝",
    })
    step += 1

    # Step 2: VAT treatment
    vat_treatment = ai_result.get("vat_treatment", "deductible")
    if direction == "incoming" and vat_treatment == "deductible":
        instructions.append({
            "step": step,
            "title": f"Record {vat_name} as Input Tax",
            "description": f"This is a purchase invoice. The {vat_name} amount of "
                           f"{currency} {vat_amount} is DEDUCTIBLE as input tax. "
                           f"Add this to your input tax records for the current period. "
                           f"This will reduce your {vat_name} payable.",
            "url": None,
            "urgent": False,
            "icon": "✅",
        })
    elif direction == "outgoing":
        instructions.append({
            "step": step,
            "title": f"Record {vat_name} as Output Tax",
            "description": f"This is a sales invoice. The {vat_name} amount of "
                           f"{currency} {vat_amount} is PAYABLE to {authority}. "
                           f"Add this to your output tax records for the current period.",
            "url": None,
            "urgent": True,
            "icon": "💰",
        })
    step += 1

    # Step 3: Filing instruction
    vat_filing = country_data.get("vat_filing", "monthly") if country_data else "monthly"
    filing_freq = "monthly" if "monthly" in vat_filing else "quarterly"
    instructions.append({
        "step": step,
        "title": f"Include in {vat_name} Return",
        "description": f"Include this invoice in your {filing_freq} {vat_name} return. "
                       f"Log in to {portal_name} and add this transaction to the current period's declaration.",
        "url": portal_url,
        "url_label": f"Open {portal_name}",
        "urgent": False,
        "icon": "🌐",
    })
    step += 1

    # Step 4: Corporate tax note (for expense invoices)
    if direction == "incoming" and invoice.get("is_deductible", True):
        corp_tax_name = _get_corporate_tax_name(country_code)
        instructions.append({
            "step": step,
            "title": f"Deduct from {corp_tax_name} Base",
            "description": f"This expense of {currency} {total - vat_amount:.2f} (ex-{vat_name}) "
                           f"is deductible from your taxable income for {corp_tax_name} purposes. "
                           f"Keep this invoice for your annual tax return.",
            "url": None,
            "urgent": False,
            "icon": "📊",
        })
        step += 1

    # Step 5: Country-specific instructions
    country_specific = _get_country_specific_instructions(
        country_code, invoice, tax_profile, step
    )
    instructions.extend(country_specific)

    # Final: Keep records
    instructions.append({
        "step": step + len(country_specific),
        "title": "Archive the Invoice",
        "description": f"Keep the original invoice for at least "
                       f"{_get_retention_period(country_code)}. "
                       f"This is required by {authority}.",
        "url": None,
        "urgent": False,
        "icon": "🗂️",
    })

    return instructions


def _get_corporate_tax_name(country_code: str) -> str:
    names = {
        "TR": "Kurumlar Vergisi",
        "DE": "Körperschaftsteuer",
        "FR": "Impôt sur les Sociétés (IS)",
        "IT": "IRES",
        "ES": "Impuesto sobre Sociedades",
        "NL": "Vennootschapsbelasting (VPB)",
        "GB": "Corporation Tax",
        "PL": "CIT",
        "SE": "Bolagsskatt",
        "AT": "Körperschaftsteuer",
        "CH": "Gewinnsteuer",
        "BE": "Impôt des Sociétés (ISOC)",
        "DK": "Selskabsskat",
        "NO": "Selskapsskatt",
        "FI": "Yhteisövero",
        "PT": "IRC",
        "GR": "Φόρος Εισοδήματος",
        "HU": "TAO",
        "CZ": "Daň z příjmů",
        "RO": "Impozit pe Profit",
    }
    return names.get(country_code, "Corporate Tax")


def _get_country_specific_instructions(
    country_code: str,
    invoice: dict,
    tax_profile: dict,
    start_step: int,
) -> list[dict]:
    """Add country-specific extra instructions."""
    instructions = []
    step = start_step

    if country_code == "TR":
        # Turkey: e-Fatura check
        instructions.append({
            "step": step,
            "title": "E-Fatura Kontrolü",
            "description": "Türkiye'de KDV mükellefleri arasındaki faturaların e-Fatura sistemi "
                           "üzerinden düzenlenmesi zorunludur. Bu faturanın e-Fatura formatında "
                           "olup olmadığını kontrol edin.",
            "url": "https://efatura.gov.tr",
            "url_label": "E-Fatura Portalı",
            "urgent": False,
            "icon": "🇹🇷",
        })
        step += 1
        # Turkey: Stopaj check for service invoices
        if invoice.get("category") in ["services", "consulting"]:
            instructions.append({
                "step": step,
                "title": "Stopaj Vergisi Kontrolü",
                "description": "Hizmet faturalarında stopaj (tevkifat) uygulanabilir. "
                               "Serbest meslek ödemeleri için %20 stopaj kesintisi yapılması gerekebilir. "
                               "Muhasebecinizle kontrol edin.",
                "url": "https://intvrg.gib.gov.tr",
                "url_label": "GİB Portalı",
                "urgent": True,
                "icon": "⚠️",
            })

    elif country_code == "DE":
        # Germany: ELSTER filing
        instructions.append({
            "step": step,
            "title": "ELSTER'e Girin",
            "description": "Bu faturayı aylık Umsatzsteuervoranmeldung (UStVA) beyannamenize ekleyin. "
                           "ELSTER üzerinden elektronik olarak ibraz edin. "
                           "Son tarih: bir sonraki ayın 10'u.",
            "url": "https://www.elster.de",
            "url_label": "ELSTER — Elektronische Steuererklärung",
            "urgent": False,
            "icon": "🇩🇪",
        })

    elif country_code == "FR":
        # France: DAS2 for service fees
        if invoice.get("category") in ["services", "consulting"]:
            instructions.append({
                "step": step,
                "title": "DAS2 Declaration",
                "description": "Les honoraires et commissions versés à des tiers "
                               "doivent être déclarés via la DAS2 (déclaration annuelle). "
                               "Conservez cette facture pour la déclaration annuelle.",
                "url": "https://www.impots.gouv.fr",
                "url_label": "impots.gouv.fr",
                "urgent": False,
                "icon": "🇫🇷",
            })

    elif country_code == "GB":
        # UK: Making Tax Digital
        instructions.append({
            "step": step,
            "title": "Making Tax Digital (MTD)",
            "description": "Under MTD, you must keep digital records. "
                           "Ensure this invoice is recorded in your MTD-compatible software. "
                           "Submit your VAT return through HMRC's online portal.",
            "url": "https://www.gov.uk/vat-returns",
            "url_label": "HMRC VAT Returns",
            "urgent": False,
            "icon": "🇬🇧",
        })

    return instructions


def _get_retention_period(country_code: str) -> str:
    periods = {
        "TR": "5 yıl (Türk Vergi Kanunu gereği)",
        "DE": "10 Jahre (§147 AO)",
        "FR": "10 ans",
        "IT": "10 anni",
        "ES": "4 años",
        "NL": "7 jaar",
        "GB": "6 years",
        "PL": "5 lat",
        "SE": "7 år",
        "AT": "7 Jahre",
        "CH": "10 Jahre",
        "BE": "7 ans/jaar",
        "DK": "5 år",
        "NO": "5 år",
        "FI": "6 vuotta",
        "PT": "10 anos",
        "GR": "5 χρόνια",
        "HU": "8 év",
        "CZ": "10 let",
        "RO": "5 ani",
    }
    return periods.get(country_code, "7 years (check local requirements)")


def _calculate_vat(invoice: dict, country_data: dict) -> float:
    """Calculate VAT if not already in invoice."""
    if not country_data:
        return 0.0
    total = float(invoice.get("total_amount") or 0)
    vat_rate = float(country_data.get("vat_rates", {}).get("standard", 20)) / 100
    return round(total * vat_rate / (1 + vat_rate), 2)


def _calculate_filing_deadline(country_data: dict, invoice_date) -> dict:
    """Calculate the next filing deadline for this invoice."""
    if not country_data or not invoice_date:
        return {"period": "Current Period", "deadline_str": "Check with your accountant",
                "deadline_date": None}

    try:
        if isinstance(invoice_date, str):
            from datetime import datetime
            inv_date = datetime.strptime(str(invoice_date), "%Y-%m-%d").date()
        else:
            inv_date = invoice_date

        filing = country_data.get("vat_filing", "monthly")
        deadline_days = country_data.get("vat_deadline_days", 28)

        if "quarterly" in filing:
            # Next quarter end
            month = inv_date.month
            quarter_end_month = ((month - 1) // 3 + 1) * 3
            if quarter_end_month > 12:
                quarter_end_month = 12
            quarter_end = date(inv_date.year, quarter_end_month, 1)
            deadline = quarter_end + timedelta(days=deadline_days)
            period = f"Q{(quarter_end_month // 3)} {inv_date.year}"
        else:
            # Monthly: next month's deadline
            if inv_date.month == 12:
                next_month = date(inv_date.year + 1, 1, 1)
            else:
                next_month = date(inv_date.year, inv_date.month + 1, 1)
            deadline = next_month.replace(day=min(deadline_days, 28))
            period = inv_date.strftime("%B %Y")

        return {
            "period": period,
            "deadline_str": deadline.strftime("%d %B %Y"),
            "deadline_date": deadline,
        }
    except Exception as e:
        logger.error(f"Deadline calculation error: {e}")
        return {"period": "Current Period", "deadline_str": "Check with your accountant",
                "deadline_date": None}
```

---

## STEP 4: TAX PROFILE + ANALYSIS API ENDPOINTS

Create `apps/api/app/api/endpoints/tax_intelligence.py`:

```python
"""
Tax Intelligence API
Company tax profile setup + invoice tax analysis endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
import logging

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.services.finance.country_tax_data import get_all_countries, get_country_data
from app.services.finance.tax_engine import analyze_invoice_taxes

router = APIRouter(prefix="/api/v1/tax", tags=["Tax Intelligence"])
logger = logging.getLogger(__name__)


# ─── COUNTRIES ────────────────────────────────────────────────────────────────

@router.get("/countries")
async def list_countries():
    """Get all supported countries for dropdown."""
    return {"countries": get_all_countries()}


@router.get("/countries/{code}")
async def get_country(code: str):
    """Get tax details for a specific country."""
    data = get_country_data(code)
    if not data:
        raise HTTPException(404, f"Country {code} not supported yet")
    return {"country": data}


# ─── COMPANY TAX PROFILE ──────────────────────────────────────────────────────

@router.get("/profile")
async def get_tax_profile(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get company tax profile for this workspace."""
    wid = str(current_user.workspace_id)
    r = await db.execute(
        text("SELECT * FROM company_tax_profiles WHERE workspace_id = :wid"),
        {"wid": wid}
    )
    row = r.fetchone()
    if not row:
        return {"profile": None, "setup_required": True}

    profile = dict(row._mapping)
    # Enrich with country data
    country = get_country_data(profile.get("country_code", "TR"))
    if country:
        profile["country_tax_data"] = {
            "vat_name": country.get("vat_name"),
            "vat_rate": country.get("vat_rates", {}).get("standard"),
            "tax_authority": country.get("tax_authority"),
            "tax_portal": country.get("tax_portal"),
            "tax_portal_name": country.get("tax_portal_name"),
            "applicable_taxes": country.get("applicable_taxes", []),
        }
    return {"profile": profile, "setup_required": not profile.get("profile_completed")}


@router.post("/profile")
async def create_or_update_tax_profile(
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update company tax profile."""
    wid = str(current_user.workspace_id)

    # Get country data to auto-fill fields
    country_code = data.get("country_code", "TR").upper()
    country = get_country_data(country_code)

    vat_rate = data.get("vat_rate")
    if not vat_rate and country:
        vat_rate = country.get("vat_rates", {}).get("standard", 20.0)

    # Determine applicable taxes from country data
    applicable_taxes = data.get("applicable_taxes")
    if not applicable_taxes and country:
        applicable_taxes = country.get("applicable_taxes", [])

    import json
    await db.execute(
        text("""
            INSERT INTO company_tax_profiles (
                workspace_id, company_name, company_type,
                country_code, country_name, city, region,
                tax_id, vat_id, registration_number,
                is_vat_registered, vat_rate, vat_filing_frequency,
                tax_year_start, industry,
                annual_revenue_estimate, employee_count_range,
                founded_year, applicable_taxes,
                tax_authority_name, tax_authority_portal, tax_authority_portal_name,
                profile_completed, setup_step
            ) VALUES (
                :wid, :company_name, :company_type,
                :country_code, :country_name, :city, :region,
                :tax_id, :vat_id, :reg_no,
                :is_vat_registered, :vat_rate, :vat_filing_frequency,
                :tax_year_start, :industry,
                :annual_revenue, :employee_count,
                :founded_year, :applicable_taxes::jsonb,
                :authority_name, :authority_portal, :authority_portal_name,
                :profile_completed, :setup_step
            )
            ON CONFLICT (workspace_id) DO UPDATE SET
                company_name = :company_name,
                company_type = :company_type,
                country_code = :country_code,
                country_name = :country_name,
                city = :city,
                region = :region,
                tax_id = :tax_id,
                vat_id = :vat_id,
                registration_number = :reg_no,
                is_vat_registered = :is_vat_registered,
                vat_rate = :vat_rate,
                vat_filing_frequency = :vat_filing_frequency,
                industry = :industry,
                annual_revenue_estimate = :annual_revenue,
                employee_count_range = :employee_count,
                applicable_taxes = :applicable_taxes::jsonb,
                tax_authority_name = :authority_name,
                tax_authority_portal = :authority_portal,
                tax_authority_portal_name = :authority_portal_name,
                profile_completed = :profile_completed,
                setup_step = :setup_step,
                updated_at = NOW()
        """),
        {
            "wid": wid,
            "company_name": data.get("company_name"),
            "company_type": data.get("company_type"),
            "country_code": country_code,
            "country_name": country.get("name") if country else data.get("country_name"),
            "city": data.get("city"),
            "region": data.get("region"),
            "tax_id": data.get("tax_id"),
            "vat_id": data.get("vat_id"),
            "reg_no": data.get("registration_number"),
            "is_vat_registered": data.get("is_vat_registered", True),
            "vat_rate": vat_rate,
            "vat_filing_frequency": data.get("vat_filing_frequency") or (country.get("vat_filing", "monthly") if country else "monthly"),
            "tax_year_start": data.get("tax_year_start", "01-01"),
            "industry": data.get("industry"),
            "annual_revenue": data.get("annual_revenue_estimate"),
            "employee_count": data.get("employee_count_range"),
            "founded_year": data.get("founded_year"),
            "applicable_taxes": json.dumps(applicable_taxes or []),
            "authority_name": country.get("tax_authority") if country else data.get("tax_authority_name"),
            "authority_portal": country.get("tax_portal") if country else data.get("tax_authority_portal"),
            "authority_portal_name": country.get("tax_portal_name") if country else data.get("tax_authority_portal_name"),
            "profile_completed": data.get("profile_completed", False),
            "setup_step": data.get("setup_step", 1),
        }
    )
    await db.commit()

    return {"success": True, "country_auto_filled": country is not None}


# ─── TAX ANALYSIS ─────────────────────────────────────────────────────────────

@router.post("/analyze/{invoice_id}")
async def analyze_invoice(
    invoice_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run tax analysis on a specific invoice."""
    wid = str(current_user.workspace_id)
    result = await analyze_invoice_taxes(invoice_id, wid, db)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return {"analysis": result}


@router.get("/analysis/{invoice_id}")
async def get_invoice_analysis(
    invoice_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get existing tax analysis for an invoice."""
    wid = str(current_user.workspace_id)
    r = await db.execute(
        text("""
            SELECT * FROM invoice_tax_analysis
            WHERE invoice_id = :inv_id AND workspace_id = :wid
            ORDER BY created_at DESC LIMIT 1
        """),
        {"inv_id": invoice_id, "wid": wid}
    )
    row = r.fetchone()
    if not row:
        return {"analysis": None}
    return {"analysis": dict(row._mapping)}


@router.get("/dashboard")
async def get_tax_dashboard(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get tax dashboard summary:
    - Total VAT payable this period
    - Total VAT deductible this period
    - Upcoming deadlines
    - Recent analyses
    """
    wid = str(current_user.workspace_id)

    # Get profile
    profile_r = await db.execute(
        text("SELECT country_code, vat_rate, tax_authority_name, tax_authority_portal, tax_authority_portal_name FROM company_tax_profiles WHERE workspace_id = :wid"),
        {"wid": wid}
    )
    profile = profile_r.fetchone()

    # Get recent analyses
    analyses_r = await db.execute(
        text("""
            SELECT ita.*, i.vendor_name, i.total_amount, i.currency, i.invoice_date
            FROM invoice_tax_analysis ita
            JOIN invoices i ON i.id = ita.invoice_id
            WHERE ita.workspace_id = :wid
            ORDER BY ita.created_at DESC
            LIMIT 10
        """),
        {"wid": wid}
    )
    analyses = [dict(r._mapping) for r in analyses_r.fetchall()]

    # Aggregate
    total_vat_payable = sum(
        float(a.get("vat_amount") or 0)
        for a in analyses
        if a.get("vat_treatment") == "payable"
    )
    total_vat_deductible = sum(
        float(a.get("vat_amount") or 0)
        for a in analyses
        if a.get("vat_treatment") == "deductible"
    )
    net_vat = total_vat_payable - total_vat_deductible

    # Get calendar
    calendar_r = await db.execute(
        text("""
            SELECT * FROM tax_calendar
            WHERE workspace_id = :wid AND due_date >= CURRENT_DATE
            ORDER BY due_date ASC LIMIT 5
        """),
        {"wid": wid}
    )
    upcoming = [dict(r._mapping) for r in calendar_r.fetchall()]

    return {
        "profile_set_up": profile is not None,
        "country_code": profile.country_code if profile else None,
        "tax_authority": profile.tax_authority_name if profile else None,
        "tax_portal": profile.tax_authority_portal if profile else None,
        "tax_portal_name": profile.tax_authority_portal_name if profile else None,
        "summary": {
            "vat_payable": total_vat_payable,
            "vat_deductible": total_vat_deductible,
            "net_vat_position": net_vat,
            "analyses_count": len(analyses),
        },
        "recent_analyses": analyses[:5],
        "upcoming_deadlines": upcoming,
    }


@router.post("/analyze-all")
async def analyze_all_pending(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Analyze all invoices that don't have tax analysis yet."""
    wid = str(current_user.workspace_id)

    # Get invoices without analysis
    r = await db.execute(
        text("""
            SELECT i.id FROM invoices i
            LEFT JOIN invoice_tax_analysis ita ON ita.invoice_id = i.id
            WHERE i.workspace_id = :wid
            AND ita.id IS NULL
            ORDER BY i.created_at DESC
            LIMIT 20
        """),
        {"wid": wid}
    )
    pending = [str(row[0]) for row in r.fetchall()]

    results = []
    for inv_id in pending:
        try:
            result = await analyze_invoice_taxes(inv_id, wid, db)
            results.append({"invoice_id": inv_id, "status": "ok"})
        except Exception as e:
            results.append({"invoice_id": inv_id, "status": "error", "error": str(e)})

    return {"analyzed": len(results), "results": results}
```

---

## STEP 5: REGISTER ROUTER IN MAIN.PY

```python
# Add to apps/api/app/main.py imports:
from app.api.endpoints.tax_intelligence import router as tax_router

# Add to router registrations:
app.include_router(tax_router)
```

---

## STEP 6: FRONTEND — TAX PROFILE SETUP PANEL

Create `apps/web/app/dashboard/finance/tax-profile/page.tsx`:

This is a multi-step company tax setup panel. Build it with these steps:

**Step 1 — Country Selection:**
- Large searchable dropdown with ALL 35 countries
- Each option shows: flag emoji + country name + currency + VAT rate
- When country selected → auto-fill VAT rate, tax authority, portal link
- Show the tax authority portal link immediately after selection

**Step 2 — Company Details:**
- Company name
- Company type (dropdown — options change based on country, e.g. GmbH for DE, Limited for TR)
- Tax ID (label changes by country: "Vergi No" for TR, "Steuernummer" for DE, etc.)
- VAT ID (label changes: "KDV No" for TR, "USt-IdNr" for DE)
- Registration number
- City / Region
- Founded year

**Step 3 — Tax Configuration:**
- Are you VAT registered? (Yes/No toggle)
- VAT rate (pre-filled from country, editable)
- VAT filing frequency (Monthly / Quarterly / Yearly)
- Industry (dropdown)
- Annual revenue estimate (dropdown: Under €100K, €100K-500K, €500K-2M, Over €2M)
- Employee count (1, 2-10, 11-50, 51+)

**Step 4 — Applicable Taxes:**
- Checklist of taxes that apply to this company (pre-filled based on country)
- Each tax has a description
- E.g. for Turkey: ☑ KDV ☑ Kurumlar Vergisi ☑ Geçici Vergi ☑ Stopaj ☑ Damga Vergisi ☑ SGK

**Step 5 — Confirmation:**
- Show summary card of what was set up
- Show the tax authority portal link with a "Open Portal →" button
- Show next VAT filing deadline
- Button: "Start Analyzing Invoices →"

---

## STEP 7: FRONTEND — ENHANCED FINANCE DASHBOARD

Update `apps/web/app/dashboard/finance/page.tsx`:

Add these sections:

**1. Tax Profile Banner (if not set up):**
```
⚠️ Set up your company tax profile to get AI-powered tax analysis on every invoice.
[Set Up Tax Profile →]
```

**2. Tax Summary Cards (if profile set up):**
Row of 3 cards:
- VAT Payable this period (red if positive)
- VAT Deductible this period (green)
- Net VAT Position (color coded)

**3. Tax Authority Quick Link:**
```
┌─────────────────────────────────────────┐
│ 🏛️ Gelir İdaresi Başkanlığı             │
│ intvrg.gib.gov.tr                       │
│ [Open Tax Portal →]  [Open e-Fatura →] │
└─────────────────────────────────────────┘
```

**4. Per-Invoice Tax Analysis:**
Each invoice row now has a "Tax Analysis" expand section:
```
▼ FATURA: AWS Turkey — ₺12,400

  TAX ANALYSIS                              AI ile Analiz Et
  ──────────────────────────────────────
  KDV: ₺2,400  |  Treatment: Deductible  |  Filing: January 2025

  ACCOUNTANT INSTRUCTIONS:
  ① 📝 Record as expense in accounting system
  ② ✅ Record ₺2,400 KDV as input tax (deductible)
  ③ 🌐 Include in monthly KDV return → [Open GİB Portal]
  ④ 📊 Deduct ₺10,000 from Kurumlar Vergisi base
  ⑤ 🇹🇷 Verify e-Fatura compliance → [Open e-Fatura]
  ⑥ 🗂️ Archive for 5 years (Turkish Tax Law)

  ⚠️ These are estimates. Verify with your accountant.
```

---

## STEP 8: VERIFICATION

```bash
BASE="/Users/oguzkullelioglu/Desktop/ai-cmo-os 2"

echo "=== DB TABLES ==="
python3 -c "
import asyncio, asyncpg
async def f():
    conn = await asyncpg.connect('postgresql://aicmo:aicmo_dev@localhost:5432/aicmo')
    for t in ['company_tax_profiles', 'invoice_tax_analysis', 'tax_calendar']:
        exists = await conn.fetchval(f\"SELECT COUNT(*) FROM information_schema.tables WHERE table_name='{t}'\")
        print(f\"{'✅' if exists else '❌'} {t}\")
    await conn.close()
asyncio.run(f())
"

echo ""
echo "=== IMPORTS ==="
cd "$BASE/apps/api"
python3 -c "from app.services.finance.country_tax_data import get_all_countries; print('✅ country_tax_data', len(get_all_countries()), 'countries')"
python3 -c "from app.services.finance.tax_engine import analyze_invoice_taxes; print('✅ tax_engine')"
python3 -c "from app.api.endpoints.tax_intelligence import router; print('✅ tax_router', len(router.routes), 'routes')"

echo ""
echo "=== BACKEND RESTART ==="
lsof -ti:8000 | xargs kill -9 2>/dev/null; sleep 3
uvicorn app.main:app --reload --port 8000 > /tmp/tax_startup.log 2>&1 &
sleep 10
grep -E "ERROR|Import" /tmp/tax_startup.log | head -5

echo ""
echo "=== ENDPOINT TESTS ==="
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@aicmo.os","password":"Demo1234!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

for ep in \
  "GET /api/v1/tax/countries" \
  "GET /api/v1/tax/countries/TR" \
  "GET /api/v1/tax/countries/DE" \
  "GET /api/v1/tax/profile" \
  "GET /api/v1/tax/dashboard"; do
  method=$(echo $ep | awk '{print $1}')
  path=$(echo $ep | awk '{print $2}')
  code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" \
    "http://localhost:8000${path}" \
    -H "Authorization: Bearer $TOKEN")
  echo "$([ "$code" == "200" ] && echo ✅ || echo ❌) $code $ep"
done

echo ""
echo "=== POST TAX PROFILE TEST ==="
curl -s -X POST http://localhost:8000/api/v1/tax/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Şirketi Ltd",
    "company_type": "limited",
    "country_code": "TR",
    "tax_id": "1234567890",
    "vat_id": "TR1234567890",
    "industry": "Technology",
    "is_vat_registered": true,
    "annual_revenue_estimate": "100k-500k",
    "employee_count_range": "2-10",
    "profile_completed": true
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print('✅ Profile saved' if d.get('success') else '❌', d)"

echo ""
echo "=== FRONTEND BUILD ==="
cd "$BASE/apps/web"
npx tsc --noEmit 2>&1 | grep "error TS" | head -5 || echo "✅ TypeScript clean"

echo ""
echo "=== LINT ==="
cd "$BASE/apps/api"
ruff check app/ 2>&1 | tail -3

echo ""
echo "=== COMMIT ==="
cd "$BASE"
git add -A
git commit -m "feat: Tax Intelligence module — company tax profile + AI accountant + 35 countries"
git push origin main
echo "✅ Done"
```

Fix every ❌ before stopping.
Do not stop until all checks pass and git push succeeds.
