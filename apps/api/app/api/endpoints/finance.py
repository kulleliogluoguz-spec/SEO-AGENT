"""Finance Module — Invoice Intelligence API."""

from __future__ import annotations

import logging
import shutil
import uuid
from datetime import date, timedelta
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.db.database import AsyncSessionLocal, get_db
from app.services.finance.invoice_intelligence import InvoiceIntelligence

router = APIRouter(prefix="/api/v1/finance", tags=["Finance"])
logger = logging.getLogger(__name__)
STORE = Path("/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/storage/invoices")
STORE.mkdir(parents=True, exist_ok=True)

DEMO_WS = "00000000-0000-0000-0001-000000000001"


def _wid(user) -> str:
    return getattr(user, "workspace_id", None) or DEMO_WS


def _row_to_dict(row) -> dict:
    if row is None:
        return {}
    out = {}
    for k, v in row._mapping.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif isinstance(v, uuid.UUID):
            out[k] = str(v)
        else:
            out[k] = v
    return out


@router.post("/invoices/upload")
async def upload_invoice(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user=Depends(get_current_user),
):
    fid = str(uuid.uuid4())
    dest = STORE / f"{fid}{Path(file.filename or '').suffix}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    background_tasks.add_task(
        _process_bg, str(dest), file.filename or dest.name, _wid(current_user)
    )
    return {
        "invoice_id": fid,
        "status": "processing",
        "message": "AI analysis will complete in 30-60 seconds.",
    }


async def _process_bg(fp: str, fn: str, wid: str) -> None:
    """Run invoice extraction in its own DB session."""
    try:
        async with AsyncSessionLocal() as db:
            await InvoiceIntelligence().process_file(fp, fn, db, wid)
    except Exception as e:
        logger.error("invoice background processing failed: %s", e)


@router.get("/invoices")
async def list_invoices(
    direction: str | None = None,
    category: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    where = "WHERE workspace_id=:wid"
    params: dict = {"wid": _wid(current_user)}
    if direction:
        where += " AND direction=:dir"
        params["dir"] = direction
    if category:
        where += " AND category=:cat"
        params["cat"] = category
    if date_from:
        where += " AND invoice_date>=:df"
        params["df"] = date_from
    if date_to:
        where += " AND invoice_date<=:dt"
        params["dt"] = date_to
    r = await db.execute(
        text(f"SELECT * FROM invoices {where} ORDER BY invoice_date DESC NULLS LAST LIMIT 100"),
        params,
    )
    invoices = [_row_to_dict(row) for row in r.fetchall()]
    return {"invoices": invoices, "total": len(invoices)}


@router.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(
        text("SELECT * FROM invoices WHERE id=:id AND workspace_id=:wid"),
        {"id": invoice_id, "wid": _wid(current_user)},
    )
    row = r.fetchone()
    if not row:
        raise HTTPException(404, "Invoice not found")
    return {"invoice": _row_to_dict(row)}


@router.put("/invoices/{invoice_id}")
async def update_invoice(
    invoice_id: str,
    data: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    allowed = [
        "vendor_name",
        "invoice_date",
        "total_amount",
        "tax_amount",
        "direction",
        "category",
        "vat_rate",
        "is_deductible",
    ]
    parts, params = [], {"id": invoice_id}
    for f in allowed:
        if f in data:
            parts.append(f"{f}=:{f}")
            params[f] = data[f]
    if parts:
        await db.execute(
            text(f"UPDATE invoices SET {', '.join(parts)}, human_reviewed=true WHERE id=:id"),
            params,
        )
        await db.commit()
    return {"success": True}


@router.get("/dashboard")
async def finance_dashboard(
    months: int = 3,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wid = _wid(current_user)
    since = date.today() - timedelta(days=months * 30)

    inc = await db.execute(
        text(
            """
            SELECT SUM(total_amount) AS total, SUM(vat_amount) AS vat, COUNT(*) AS cnt
            FROM invoices
            WHERE workspace_id=:wid AND direction='outgoing'
              AND invoice_date>=:since AND extraction_status='completed'
            """
        ),
        {"wid": wid, "since": since},
    )
    income = _row_to_dict(inc.fetchone())

    exp = await db.execute(
        text(
            """
            SELECT SUM(total_amount) AS total, SUM(vat_amount) AS vat, COUNT(*) AS cnt
            FROM invoices
            WHERE workspace_id=:wid AND direction='incoming'
              AND invoice_date>=:since AND extraction_status='completed'
            """
        ),
        {"wid": wid, "since": since},
    )
    expenses = _row_to_dict(exp.fetchone())

    cats = await db.execute(
        text(
            """
            SELECT category, direction, SUM(total_amount) AS total, COUNT(*) AS cnt
            FROM invoices
            WHERE workspace_id=:wid AND invoice_date>=:since
              AND extraction_status='completed'
            GROUP BY category, direction
            ORDER BY total DESC
            """
        ),
        {"wid": wid, "since": since},
    )
    categories = [_row_to_dict(r) for r in cats.fetchall()]

    ti = float(income.get("total") or 0)
    te = float(expenses.get("total") or 0)
    vi = float(income.get("vat") or 0)
    ve = float(expenses.get("vat") or 0)

    return {
        "period_months": months,
        "income": {
            "total": ti,
            "vat_collected": vi,
            "net": ti - vi,
            "invoice_count": int(income.get("cnt") or 0),
        },
        "expenses": {
            "total": te,
            "vat_paid": ve,
            "net": te - ve,
            "invoice_count": int(expenses.get("cnt") or 0),
        },
        "profit_loss": {
            "gross": ti - te,
            "net_of_vat": (ti - vi) - (te - ve),
            "estimated_net_vat_payable": max(vi - ve, 0),
            "estimated_vat_refundable": max(ve - vi, 0),
        },
        "categories": categories,
        "disclaimer": "⚠️ Estimates only. Consult your accountant for official tax filing.",
    }
