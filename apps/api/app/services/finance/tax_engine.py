"""
Tax Analysis Engine

Analyzes invoices against the company's tax profile and country-specific
tax rules. Generates step-by-step accountant instructions including portal
links, filing deadlines, and local-language notes.

Uses:
  - Company tax profile (from DB)
  - Country tax database (static, from country_tax_data.py)
  - Local Ollama AI for contextual tax treatment decisions
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timedelta

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.model_config import ModelSelector
from app.services.finance.country_tax_data import get_country_data

logger = logging.getLogger(__name__)

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


# ─── Main entry point ────────────────────────────────────────────────────────


async def analyze_invoice_taxes(
    invoice_id: str,
    workspace_id: str,
    db: AsyncSession,
) -> dict:
    """Analyze a single invoice for tax implications. Returns the full analysis dict."""

    # 1. Load invoice
    inv_r = await db.execute(
        text("SELECT * FROM invoices WHERE id = :id AND workspace_id = :wid"),
        {"id": invoice_id, "wid": workspace_id},
    )
    invoice = inv_r.fetchone()
    if not invoice:
        return {"error": "Invoice not found"}
    invoice = dict(invoice._mapping)

    # 2. Load company tax profile
    prof_r = await db.execute(
        text("SELECT * FROM company_tax_profiles WHERE workspace_id = :wid"),
        {"wid": workspace_id},
    )
    tax_profile = prof_r.fetchone()
    if not tax_profile:
        return {"error": "Company tax profile not set up. Go to Setup → Tax Profile first."}
    tax_profile = dict(tax_profile._mapping)

    country_code = tax_profile.get("country_code", "TR")
    country_data = get_country_data(country_code)

    # 3. Build prompt and call AI
    prompt = _build_tax_analysis_prompt(invoice, tax_profile, country_data)
    ai_result = await _call_ai_tax_analysis(prompt)

    # 4. Generate step-by-step instructions
    instructions = _generate_instructions(ai_result, invoice, tax_profile, country_data)

    # 5. Calculate filing deadline
    filing = _calculate_filing_deadline(country_data, invoice.get("invoice_date"))

    # 6. Assemble result
    vat_name_prefix = (
        country_data.get("vat_name", "VAT").split()[0].upper() if country_data else "VAT"
    )
    result: dict = {
        "invoice_id": invoice_id,
        "workspace_id": workspace_id,
        "country_code": country_code,
        "tax_regime": f"{country_code}_{vat_name_prefix}",
        "invoice_direction": invoice.get("direction", "incoming"),
        "vat_amount": invoice.get("vat_amount") or _calculate_vat(invoice, country_data),
        "vat_rate": tax_profile.get("vat_rate")
        or (country_data.get("vat_rates", {}).get("standard") if country_data else 20.0),
        "vat_treatment": ai_result.get("vat_treatment", "deductible"),
        "vat_action": ai_result.get("vat_action", ""),
        "other_taxes": ai_result.get("other_taxes", []),
        "total_tax_impact": ai_result.get("total_tax_impact", 0),
        "net_tax_payable": ai_result.get("net_tax_payable", 0),
        "filing_period": filing.get("period"),
        "filing_deadline": filing.get("deadline_str"),
        "filing_deadline_date": filing.get("deadline_date"),
        "authority_name": (country_data.get("tax_authority") if country_data else ""),
        "authority_portal_url": (country_data.get("tax_portal") if country_data else ""),
        "authority_portal_name": (country_data.get("tax_portal_name") if country_data else ""),
        "instructions": instructions,
        "ai_explanation": ai_result.get("explanation", ""),
        "ai_warnings": ai_result.get("warnings", []),
        "confidence_score": 0.85,
        "ai_model_used": ModelSelector.get_best_model(),
    }

    # 7. Persist to DB (CAST used to avoid SQLAlchemy ::jsonb bind regression)
    await db.execute(
        text(
            """
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
                :vat_action, CAST(:other_taxes AS jsonb), :total_tax_impact,
                :net_tax_payable, :filing_period, :filing_deadline,
                :filing_deadline_date, :authority_name, :authority_portal_url,
                :authority_portal_name, CAST(:instructions AS jsonb),
                :ai_explanation, :ai_warnings,
                :confidence_score, :ai_model_used
            )
            ON CONFLICT DO NOTHING
            """
        ),
        {
            **result,
            "other_taxes": json.dumps(result["other_taxes"]),
            "instructions": json.dumps(result["instructions"]),
        },
    )
    await db.commit()

    return result


# ─── AI prompt ────────────────────────────────────────────────────────────────


def _build_tax_analysis_prompt(invoice: dict, tax_profile: dict, country_data: dict | None) -> str:
    country_name = tax_profile.get("country_name", "Unknown")
    company_type = tax_profile.get("company_type", "limited")
    vat_registered = tax_profile.get("is_vat_registered", True)
    direction = invoice.get("direction", "incoming")

    vat_name = country_data.get("vat_name", "VAT") if country_data else "VAT"
    vat_rate = country_data.get("vat_rates", {}).get("standard", 20) if country_data else 20
    authority = country_data.get("tax_authority", "") if country_data else ""
    portal = country_data.get("tax_portal", "") if country_data else ""
    applicable = country_data.get("applicable_taxes", []) if country_data else []
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
- Applicable taxes: {', '.join(applicable)}
- Tax authority: {authority}
- Tax portal: {portal}
- Notes: {notes}

Analyze this invoice and respond ONLY with valid JSON:
{{
  "vat_treatment": "deductible|payable|exempt|reverse_charge",
  "vat_action": "what to do with the VAT amount",
  "net_tax_payable": 0,
  "total_tax_impact": 0,
  "other_taxes": [],
  "explanation": "plain language explanation for the accountant",
  "warnings": [],
  "filing_category": "which tax return this goes into"
}}"""


# ─── AI call ──────────────────────────────────────────────────────────────────


async def _call_ai_tax_analysis(prompt: str) -> dict:
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
                },
            )
            if not r.is_success:
                logger.error("AI tax analysis failed: %s", r.status_code)
                return _fallback_result()

            raw = r.json().get("response", "")
            if "<think>" in raw:
                raw = raw.split("</think>")[-1].strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            # Find first { and last }
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
            return _fallback_result()
    except Exception as e:
        logger.error("AI tax analysis error: %s", e)
        return _fallback_result()


def _fallback_result() -> dict:
    return {
        "vat_treatment": "deductible",
        "vat_action": "Include in VAT return as input tax",
        "net_tax_payable": 0,
        "total_tax_impact": 0,
        "other_taxes": [],
        "explanation": "Automatic analysis unavailable. Please review manually.",
        "warnings": ["Manual review recommended"],
    }


# ─── Instructions generator ──────────────────────────────────────────────────


def _generate_instructions(
    ai_result: dict,
    invoice: dict,
    tax_profile: dict,
    country_data: dict | None,
) -> list[dict]:
    instructions: list[dict] = []
    step = 1

    country_code = tax_profile.get("country_code", "TR")
    portal_url = country_data.get("tax_portal", "#") if country_data else "#"
    portal_name = (
        country_data.get("tax_portal_name", "Tax Portal") if country_data else "Tax Portal"
    )
    authority = (
        country_data.get("tax_authority", "Tax Authority") if country_data else "Tax Authority"
    )
    vat_name = country_data.get("vat_name", "VAT") if country_data else "VAT"
    direction = invoice.get("direction", "incoming")
    currency = invoice.get("currency", "")
    vat_amount = float(invoice.get("vat_amount") or 0)
    total = float(invoice.get("total_amount") or 0)
    vendor = invoice.get("vendor_name", "vendor")
    inv_date = invoice.get("invoice_date", "")

    # Record invoice
    instructions.append(
        {
            "step": step,
            "title": "Record the Invoice",
            "description": (
                f"Record this {'expense' if direction == 'incoming' else 'income'} "
                f"invoice from {vendor} for {currency} {total} in your accounting system. "
                f"Invoice date: {inv_date}."
            ),
            "url": None,
            "urgent": False,
            "icon": "📝",
        }
    )
    step += 1

    # VAT treatment
    vat_treatment = ai_result.get("vat_treatment", "deductible")
    if direction == "incoming" and vat_treatment == "deductible":
        instructions.append(
            {
                "step": step,
                "title": f"Record {vat_name} as Input Tax",
                "description": (
                    f"The {vat_name} amount of {currency} {vat_amount} is DEDUCTIBLE. "
                    f"Add to your input tax records for the current period."
                ),
                "url": None,
                "urgent": False,
                "icon": "✅",
            }
        )
    elif direction == "outgoing":
        instructions.append(
            {
                "step": step,
                "title": f"Record {vat_name} as Output Tax",
                "description": (
                    f"The {vat_name} amount of {currency} {vat_amount} is PAYABLE to {authority}."
                ),
                "url": None,
                "urgent": True,
                "icon": "💰",
            }
        )
    step += 1

    # Filing instruction
    vat_filing = country_data.get("vat_filing", "monthly") if country_data else "monthly"
    freq = "monthly" if "monthly" in vat_filing else "quarterly"
    instructions.append(
        {
            "step": step,
            "title": f"Include in {vat_name} Return",
            "description": (
                f"Include in your {freq} {vat_name} return. " f"Log in to {portal_name} and submit."
            ),
            "url": portal_url,
            "url_label": f"Open {portal_name}",
            "urgent": False,
            "icon": "🌐",
        }
    )
    step += 1

    # Corporate tax deduction (for expenses)
    if direction == "incoming" and invoice.get("is_deductible", True):
        corp_name = _CORP_TAX_NAMES.get(country_code, "Corporate Tax")
        net_amount = total - vat_amount
        instructions.append(
            {
                "step": step,
                "title": f"Deduct from {corp_name} Base",
                "description": (
                    f"This expense of {currency} {net_amount:.2f} (ex-{vat_name}) "
                    f"is deductible from your taxable income."
                ),
                "url": None,
                "urgent": False,
                "icon": "📊",
            }
        )
        step += 1

    # Country-specific extras
    extras = _country_extras(country_code, invoice, step)
    instructions.extend(extras)
    step += len(extras)

    # Archive
    retention = _RETENTION.get(country_code, "7 years")
    instructions.append(
        {
            "step": step,
            "title": "Archive the Invoice",
            "description": f"Keep the original invoice for at least {retention}. Required by {authority}.",
            "url": None,
            "urgent": False,
            "icon": "🗂️",
        }
    )

    return instructions


# ─── Helpers ──────────────────────────────────────────────────────────────────

_CORP_TAX_NAMES: dict[str, str] = {
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

_RETENTION: dict[str, str] = {
    "TR": "5 yıl (Türk Vergi Kanunu)",
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


def _country_extras(country_code: str, invoice: dict, start_step: int) -> list[dict]:
    extras: list[dict] = []
    s = start_step
    if country_code == "TR":
        extras.append(
            {
                "step": s,
                "title": "E-Fatura Kontrolü",
                "description": (
                    "KDV mükellefleri arasındaki faturaların e-Fatura sistemi "
                    "üzerinden düzenlenmesi zorunludur. Bu faturanın e-Fatura "
                    "formatında olduğunu doğrulayın."
                ),
                "url": "https://efatura.gov.tr",
                "url_label": "E-Fatura Portalı",
                "urgent": False,
                "icon": "🇹🇷",
            }
        )
        s += 1
        if invoice.get("category") in ("services", "consulting"):
            extras.append(
                {
                    "step": s,
                    "title": "Stopaj Vergisi Kontrolü",
                    "description": (
                        "Hizmet faturalarında stopaj uygulanabilir. "
                        "Serbest meslek ödemeleri için %20 stopaj gerekebilir."
                    ),
                    "url": "https://intvrg.gib.gov.tr",
                    "url_label": "GİB Portalı",
                    "urgent": True,
                    "icon": "⚠️",
                }
            )
    elif country_code == "DE":
        extras.append(
            {
                "step": s,
                "title": "ELSTER Filing",
                "description": (
                    "Include in your monthly Umsatzsteuervoranmeldung (UStVA). "
                    "File electronically via ELSTER. Deadline: 10th of following month."
                ),
                "url": "https://www.elster.de",
                "url_label": "ELSTER",
                "urgent": False,
                "icon": "🇩🇪",
            }
        )
    elif country_code == "GB":
        extras.append(
            {
                "step": s,
                "title": "Making Tax Digital (MTD)",
                "description": (
                    "Ensure this invoice is recorded in your MTD-compatible software. "
                    "Submit your VAT return through HMRC."
                ),
                "url": "https://www.gov.uk/vat-returns",
                "url_label": "HMRC VAT Returns",
                "urgent": False,
                "icon": "🇬🇧",
            }
        )
    elif country_code == "FR":
        if invoice.get("category") in ("services", "consulting"):
            extras.append(
                {
                    "step": s,
                    "title": "DAS2 Declaration",
                    "description": (
                        "Les honoraires versés à des tiers doivent être déclarés "
                        "via la DAS2 (déclaration annuelle)."
                    ),
                    "url": "https://www.impots.gouv.fr",
                    "url_label": "impots.gouv.fr",
                    "urgent": False,
                    "icon": "🇫🇷",
                }
            )
    return extras


def _calculate_vat(invoice: dict, country_data: dict | None) -> float:
    if not country_data:
        return 0.0
    total = float(invoice.get("total_amount") or 0)
    rate = float(country_data.get("vat_rates", {}).get("standard", 20)) / 100
    return round(total * rate / (1 + rate), 2)


def _calculate_filing_deadline(country_data: dict | None, invoice_date: date | str | None) -> dict:
    if not country_data or not invoice_date:
        return {
            "period": "Current Period",
            "deadline_str": "Check with your accountant",
            "deadline_date": None,
        }
    try:
        if isinstance(invoice_date, str):
            inv_date = datetime.strptime(str(invoice_date), "%Y-%m-%d").date()
        else:
            inv_date = invoice_date

        filing = country_data.get("vat_filing", "monthly")
        dd = country_data.get("vat_deadline_days", 28)

        if "quarterly" in filing:
            qm = ((inv_date.month - 1) // 3 + 1) * 3
            qm = min(qm, 12)
            qe = date(inv_date.year, qm, 1)
            deadline = qe + timedelta(days=dd)
            period = f"Q{qm // 3} {inv_date.year}"
        else:
            nm = date(
                inv_date.year + (1 if inv_date.month == 12 else 0), (inv_date.month % 12) + 1, 1
            )
            deadline = nm.replace(day=min(dd, 28))
            period = inv_date.strftime("%B %Y")

        return {
            "period": period,
            "deadline_str": deadline.strftime("%d %B %Y"),
            "deadline_date": deadline,
        }
    except Exception as e:
        logger.error("Filing deadline calc error: %s", e)
        return {
            "period": "Current Period",
            "deadline_str": "Check with your accountant",
            "deadline_date": None,
        }
