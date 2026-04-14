"""
Tax Intelligence API

Company tax profile setup, per-invoice tax analysis, and tax dashboard.
"""

from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.db.database import get_db
from app.services.finance.country_tax_data import get_all_countries, get_country_data
from app.services.finance.tax_engine import analyze_invoice_taxes

router = APIRouter(prefix="/api/v1/tax", tags=["Tax Intelligence"])
logger = logging.getLogger(__name__)

DEMO_WS = "00000000-0000-0000-0001-000000000001"


def _wid(user) -> str:
    return getattr(user, "workspace_id", None) or DEMO_WS


def _row_to_dict(row) -> dict:
    if row is None:
        return {}
    out: dict = {}
    for k, v in row._mapping.items():
        if isinstance(v, uuid.UUID):
            out[k] = str(v)
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


# ─── COUNTRIES ────────────────────────────────────────────────────────────────


@router.get("/countries")
async def list_countries():
    """All supported countries for dropdown."""
    return {"countries": get_all_countries()}


@router.get("/countries/{code}")
async def get_country(code: str):
    """Tax details for a specific country."""
    data = get_country_data(code)
    if not data:
        raise HTTPException(404, f"Country {code} not supported yet")
    return {"country": data}


# ─── COMPANY TAX PROFILE ─────────────────────────────────────────────────────


@router.get("/profile")
async def get_tax_profile(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get company tax profile for this workspace."""
    wid = _wid(current_user)
    r = await db.execute(
        text("SELECT * FROM company_tax_profiles WHERE workspace_id = :wid"),
        {"wid": wid},
    )
    row = r.fetchone()
    if not row:
        return {"profile": None, "setup_required": True}

    profile = _row_to_dict(row)
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
    wid = _wid(current_user)

    country_code = (data.get("country_code") or "TR").upper()
    country = get_country_data(country_code)

    vat_rate = data.get("vat_rate")
    if not vat_rate and country:
        vat_rate = country.get("vat_rates", {}).get("standard", 20.0)

    applicable_taxes = data.get("applicable_taxes")
    if not applicable_taxes and country:
        applicable_taxes = country.get("applicable_taxes", [])

    await db.execute(
        text(
            """
            INSERT INTO company_tax_profiles (
                workspace_id, company_name, company_type,
                country_code, country_name, city, region,
                tax_id, vat_id, registration_number,
                is_vat_registered, vat_rate, vat_filing_frequency,
                tax_year_start, industry,
                annual_revenue_estimate, employee_count_range,
                founded_year, applicable_taxes,
                tax_authority_name, tax_authority_portal,
                tax_authority_portal_name,
                profile_completed, setup_step
            ) VALUES (
                :wid, :company_name, :company_type,
                :country_code, :country_name, :city, :region,
                :tax_id, :vat_id, :reg_no,
                :is_vat_registered, :vat_rate, :vat_filing_frequency,
                :tax_year_start, :industry,
                :annual_revenue, :employee_count,
                :founded_year, CAST(:applicable_taxes AS jsonb),
                :authority_name, :authority_portal,
                :authority_portal_name,
                :profile_completed, :setup_step
            )
            ON CONFLICT (workspace_id) DO UPDATE SET
                company_name = EXCLUDED.company_name,
                company_type = EXCLUDED.company_type,
                country_code = EXCLUDED.country_code,
                country_name = EXCLUDED.country_name,
                city = EXCLUDED.city,
                region = EXCLUDED.region,
                tax_id = EXCLUDED.tax_id,
                vat_id = EXCLUDED.vat_id,
                registration_number = EXCLUDED.registration_number,
                is_vat_registered = EXCLUDED.is_vat_registered,
                vat_rate = EXCLUDED.vat_rate,
                vat_filing_frequency = EXCLUDED.vat_filing_frequency,
                industry = EXCLUDED.industry,
                annual_revenue_estimate = EXCLUDED.annual_revenue_estimate,
                employee_count_range = EXCLUDED.employee_count_range,
                applicable_taxes = EXCLUDED.applicable_taxes,
                tax_authority_name = EXCLUDED.tax_authority_name,
                tax_authority_portal = EXCLUDED.tax_authority_portal,
                tax_authority_portal_name = EXCLUDED.tax_authority_portal_name,
                profile_completed = EXCLUDED.profile_completed,
                setup_step = EXCLUDED.setup_step,
                updated_at = NOW()
            """
        ),
        {
            "wid": wid,
            "company_name": data.get("company_name"),
            "company_type": data.get("company_type"),
            "country_code": country_code,
            "country_name": (country.get("name") if country else data.get("country_name")),
            "city": data.get("city"),
            "region": data.get("region"),
            "tax_id": data.get("tax_id"),
            "vat_id": data.get("vat_id"),
            "reg_no": data.get("registration_number"),
            "is_vat_registered": data.get("is_vat_registered", True),
            "vat_rate": vat_rate,
            "vat_filing_frequency": (
                data.get("vat_filing_frequency")
                or (country.get("vat_filing", "monthly") if country else "monthly")
            ),
            "tax_year_start": data.get("tax_year_start", "01-01"),
            "industry": data.get("industry"),
            "annual_revenue": data.get("annual_revenue_estimate"),
            "employee_count": data.get("employee_count_range"),
            "founded_year": data.get("founded_year"),
            "applicable_taxes": json.dumps(applicable_taxes or []),
            "authority_name": (
                country.get("tax_authority") if country else data.get("tax_authority_name")
            ),
            "authority_portal": (
                country.get("tax_portal") if country else data.get("tax_authority_portal")
            ),
            "authority_portal_name": (
                country.get("tax_portal_name") if country else data.get("tax_authority_portal_name")
            ),
            "profile_completed": data.get("profile_completed", False),
            "setup_step": data.get("setup_step", 1),
        },
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
    wid = _wid(current_user)
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
    wid = _wid(current_user)
    r = await db.execute(
        text(
            """
            SELECT * FROM invoice_tax_analysis
            WHERE invoice_id = :inv_id AND workspace_id = :wid
            ORDER BY created_at DESC LIMIT 1
            """
        ),
        {"inv_id": invoice_id, "wid": wid},
    )
    row = r.fetchone()
    if not row:
        return {"analysis": None}
    return {"analysis": _row_to_dict(row)}


@router.get("/dashboard")
async def get_tax_dashboard(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tax dashboard — VAT summary, recent analyses, upcoming deadlines."""
    wid = _wid(current_user)

    profile_r = await db.execute(
        text(
            "SELECT country_code, vat_rate, tax_authority_name, "
            "tax_authority_portal, tax_authority_portal_name "
            "FROM company_tax_profiles WHERE workspace_id = :wid"
        ),
        {"wid": wid},
    )
    profile = profile_r.fetchone()

    analyses_r = await db.execute(
        text(
            """
            SELECT ita.*, i.vendor_name, i.total_amount, i.currency, i.invoice_date
            FROM invoice_tax_analysis ita
            JOIN invoices i ON i.id = ita.invoice_id
            WHERE ita.workspace_id = :wid
            ORDER BY ita.created_at DESC
            LIMIT 10
            """
        ),
        {"wid": wid},
    )
    analyses = [_row_to_dict(r) for r in analyses_r.fetchall()]

    total_vat_payable = sum(
        float(a.get("vat_amount") or 0) for a in analyses if a.get("vat_treatment") == "payable"
    )
    total_vat_deductible = sum(
        float(a.get("vat_amount") or 0) for a in analyses if a.get("vat_treatment") == "deductible"
    )

    calendar_r = await db.execute(
        text(
            """
            SELECT * FROM tax_calendar
            WHERE workspace_id = :wid AND due_date >= CURRENT_DATE
            ORDER BY due_date ASC LIMIT 5
            """
        ),
        {"wid": wid},
    )
    upcoming = [_row_to_dict(r) for r in calendar_r.fetchall()]

    return {
        "profile_set_up": profile is not None,
        "country_code": profile.country_code if profile else None,
        "tax_authority": profile.tax_authority_name if profile else None,
        "tax_portal": profile.tax_authority_portal if profile else None,
        "tax_portal_name": profile.tax_authority_portal_name if profile else None,
        "summary": {
            "vat_payable": total_vat_payable,
            "vat_deductible": total_vat_deductible,
            "net_vat_position": total_vat_payable - total_vat_deductible,
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
    """Analyze all invoices that don't have a tax analysis yet."""
    wid = _wid(current_user)

    r = await db.execute(
        text(
            """
            SELECT i.id FROM invoices i
            LEFT JOIN invoice_tax_analysis ita ON ita.invoice_id = i.id
            WHERE i.workspace_id = :wid AND ita.id IS NULL
            ORDER BY i.created_at DESC
            LIMIT 20
            """
        ),
        {"wid": wid},
    )
    pending = [str(row[0]) for row in r.fetchall()]

    results = []
    for inv_id in pending:
        try:
            await analyze_invoice_taxes(inv_id, wid, db)
            results.append({"invoice_id": inv_id, "status": "ok"})
        except Exception as e:
            results.append({"invoice_id": inv_id, "status": "error", "error": str(e)[:100]})

    return {"analyzed": len(results), "results": results}
