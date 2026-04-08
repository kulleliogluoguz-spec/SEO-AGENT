"""
Invoice Intelligence — OCR + LLM field extraction + Turkish tax classification.

The whole pipeline degrades gracefully when optional OCR backends
(paddleocr / pytesseract) aren't installed: text-only PDFs still work
via pdfplumber, and structured extraction always falls back to local Ollama.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from sqlalchemy import text as sqla_text

from app.services.ai.model_config import TaskType, call_ollama, call_ollama_json

logger = logging.getLogger(__name__)
STORAGE = Path("/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/storage/invoices")
STORAGE.mkdir(parents=True, exist_ok=True)

DISCLAIMER = (
    "⚠️ Bu analiz yapay zeka tarafından oluşturulmuş bir TAHMİNDİR. "
    "Vergi yükümlülükleriniz için mali müşavirinize danışın."
)

TR_KDV = {
    "food_basic": 1,
    "food_processed": 10,
    "medicine": 10,
    "software": 20,
    "marketing": 20,
    "professional_services": 20,
    "advertising": 20,
    "office": 20,
    "general": 20,
    "exempt": 0,
}


class InvoiceIntelligence:
    # ── Text extraction ──────────────────────────────────────────────────────
    def extract_text(self, file_path: str) -> str:
        path = Path(file_path)
        if path.suffix.lower() == ".pdf":
            text = self._pdf_text(file_path)
            if len(text.strip()) > 50:
                return text
            return self._ocr_pdf(file_path)
        return self._ocr_image(file_path)

    def _pdf_text(self, fp: str) -> str:
        try:
            import pdfplumber  # type: ignore

            parts: list[str] = []
            with pdfplumber.open(fp) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        parts.append(t)
            return "\n".join(parts)
        except Exception as e:
            logger.error("PDF text extraction failed: %s", e)
            return ""

    def _ocr_pdf(self, fp: str) -> str:
        try:
            import os
            import tempfile

            from pdf2image import convert_from_path  # type: ignore

            pages = convert_from_path(fp, dpi=200)
            texts: list[str] = []
            for page in pages:
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    page.save(tmp.name, "JPEG")
                    texts.append(self._ocr_image(tmp.name))
                    os.unlink(tmp.name)
            return "\n".join(texts)
        except Exception as e:
            logger.warning("PDF OCR not available (%s)", e)
            return ""

    def _ocr_image(self, fp: str) -> str:
        try:
            from paddleocr import PaddleOCR  # type: ignore

            ocr = PaddleOCR(use_angle_cls=True, lang="tr", show_log=False)
            result = ocr.ocr(fp)
            if not result or not result[0]:
                return ""
            return "\n".join(line[1][0] for line in result[0] if line[1][0].strip())
        except Exception:
            try:
                import pytesseract  # type: ignore
                from PIL import Image  # type: ignore

                return pytesseract.image_to_string(Image.open(fp), lang="tur+eng")
            except Exception as e:
                logger.warning("OCR not available (%s)", e)
                return ""

    # ── LLM extraction ───────────────────────────────────────────────────────
    def extract_fields(self, raw_text: str, file_name: str = "") -> dict:
        if not raw_text or len(raw_text.strip()) < 20:
            return {"error": "Insufficient text extracted"}
        schema = {
            "invoice_number": "INV-001",
            "invoice_date": "2024-01-15",
            "due_date": "2024-02-15",
            "vendor_name": "Example Co",
            "vendor_tax_id": "1234567890",
            "customer_name": "My Co",
            "customer_tax_id": "0987654321",
            "currency": "TRY",
            "subtotal": 1000.0,
            "tax_amount": 200.0,
            "total_amount": 1200.0,
            "vat_rate": 20,
            "direction": "incoming",
            "category": "software",
            "description": "Software license",
            "line_items": [],
            "confidence": 0.85,
        }
        prompt = f"""Extract structured data from this invoice/receipt.

DOCUMENT:
{raw_text[:4000]}

FILE: {file_name}

direction: 'incoming'=expense we received, 'outgoing'=income we issued
category: software|marketing|office|travel|professional_services|hardware|utilities|rent|food|advertising|general
If field not found use null. Estimate confidence 0-1."""
        return call_ollama_json(prompt, schema, task=TaskType.REASONING, timeout=120)

    # ── Tax logic (Turkey) ───────────────────────────────────────────────────
    def classify_tax(self, data: dict) -> dict:
        category = data.get("category") or "general"
        direction = data.get("direction") or "incoming"
        try:
            total = float(data.get("total_amount") or 0)
        except Exception:
            total = 0.0
        try:
            vat_rate = float(data.get("vat_rate") or TR_KDV.get(category, 20))
        except Exception:
            vat_rate = float(TR_KDV.get(category, 20))
        try:
            vat_amount = float(data.get("tax_amount") or total * vat_rate / (100 + vat_rate))
        except Exception:
            vat_amount = 0.0

        result = {
            "vat_rate": vat_rate,
            "vat_amount": round(vat_amount, 2),
            "is_deductible": direction == "incoming",
            "tax_category": category,
            "disclaimer": DISCLAIMER,
        }
        net = total - vat_amount
        currency = data.get("currency", "TRY")
        if direction == "incoming":
            result["estimated_tax_impact"] = (
                f"Gider faturası: {vat_rate}% KDV ({vat_amount:.2f} {currency}) "
                f"mahsup edilebilir. Net gider: {net:.2f}"
            )
            result["bookkeeping_account"] = "770 - Genel Yönetim Giderleri"
        else:
            result["estimated_tax_impact"] = (
                f"Satış faturası: {vat_rate}% KDV ({vat_amount:.2f} {currency}) "
                f"beyan edilmeli. Net gelir: {net:.2f}"
            )
            result["bookkeeping_account"] = "600 - Yurt İçi Satışlar"
        return result

    def generate_insight(self, invoice: dict, tax: dict) -> str:
        prompt = f"""You are an accounting assistant. Brief practical insight for this invoice.
Vendor: {invoice.get('vendor_name')} | Date: {invoice.get('invoice_date')}
Amount: {invoice.get('total_amount')} {invoice.get('currency', 'TRY')} | VAT: {tax.get('vat_amount')} ({tax.get('vat_rate')}%)
Type: {invoice.get('direction', 'incoming')} | Category: {invoice.get('category')}
Write 2-3 sentences: what this is, VAT impact, one accounting note.
End with: "Please verify with your accountant before filing." """
        return call_ollama(prompt, task=TaskType.STANDARD, max_tokens=200, timeout=60)

    async def process_file(self, file_path: str, file_name: str, db, workspace_id: str) -> dict:
        raw = self.extract_text(file_path)
        data = self.extract_fields(raw, file_name)
        if "error" in data:
            return {"error": data["error"]}
        tax = self.classify_tax(data)
        insight = self.generate_insight(data, tax)
        inv_id = str(uuid.uuid4())
        await db.execute(
            sqla_text(
                """
                INSERT INTO invoices(
                    id, workspace_id, file_path, file_name, file_type,
                    invoice_number, invoice_date, due_date,
                    vendor_name, vendor_tax_id, customer_name, customer_tax_id,
                    currency, subtotal, tax_amount, total_amount,
                    direction, category, vat_rate, vat_amount, is_deductible,
                    estimated_tax_impact, ai_notes, line_items, confidence_score,
                    extraction_status
                )
                VALUES(
                    :id, :wid, :fp, :fn, :ft,
                    :inum, :idate, :ddate,
                    :vendor, :vtax, :cust, :ctax,
                    :curr, :sub, :tax_amt, :total,
                    :dir, :cat, :vrate, :vamt, :deduct,
                    :taximp, :notes, CAST(:items AS jsonb), :conf,
                    'completed'
                )
                """
            ),
            {
                "id": inv_id,
                "wid": workspace_id,
                "fp": file_path,
                "fn": file_name,
                "ft": Path(file_name).suffix.lower().lstrip("."),
                "inum": data.get("invoice_number"),
                "idate": data.get("invoice_date"),
                "ddate": data.get("due_date"),
                "vendor": data.get("vendor_name"),
                "vtax": data.get("vendor_tax_id"),
                "cust": data.get("customer_name"),
                "ctax": data.get("customer_tax_id"),
                "curr": data.get("currency", "TRY"),
                "sub": data.get("subtotal"),
                "tax_amt": data.get("tax_amount"),
                "total": data.get("total_amount"),
                "dir": data.get("direction", "incoming"),
                "cat": data.get("category"),
                "vrate": tax.get("vat_rate"),
                "vamt": tax.get("vat_amount"),
                "deduct": tax.get("is_deductible", False),
                "taximp": tax.get("estimated_tax_impact"),
                "notes": f"{insight}\n\n{DISCLAIMER}",
                "items": json.dumps(data.get("line_items", []) or []),
                "conf": data.get("confidence", 0.5),
            },
        )
        await db.commit()
        return {
            "invoice_id": inv_id,
            "invoice_data": data,
            "tax_analysis": tax,
            "ai_insight": insight,
            "disclaimer": DISCLAIMER,
        }
