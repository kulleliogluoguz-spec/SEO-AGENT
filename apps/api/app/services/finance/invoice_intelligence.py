"""
Invoice Intelligence — OCR + LLM field extraction + Turkish tax classification.

Inspired by TaxHacker's structured schema approach:
- Strict JSON schema sent to the LLM (no free-form output)
- Line-item splitting: each product/service is extracted individually
- Turkish invoice handling (KDV = VAT, Fatura = Invoice)
- Multi-currency support
- Graceful degradation when optional OCR backends aren't installed

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

# ─── Valid categories for the LLM to pick from ──────────────────────────────
VALID_CATEGORIES = [
    "software",
    "advertising",
    "payroll",
    "office",
    "travel",
    "services",
    "products",
    "utilities",
    "other",
]

# ─── JSON Schema (TaxHacker-inspired) ───────────────────────────────────────
# Sent to the LLM as the expected output format. Uses "required" +
# "additionalProperties: false" for strict compliance. The `items` array
# mirrors TaxHacker's `fieldsToJsonSchema()` pattern where each line item
# repeats the field schema.

EXTRACTION_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "invoice_number": {
            "type": "string",
            "description": "Invoice/receipt number (Fatura No)",
        },
        "invoice_date": {
            "type": "string",
            "description": "Issue date in YYYY-MM-DD format (Fatura Tarihi)",
        },
        "due_date": {
            "type": "string",
            "description": "Payment due date in YYYY-MM-DD format (Son Ödeme Tarihi). null if not present.",
        },
        "vendor_name": {
            "type": "string",
            "description": "Name of the company that issued the invoice (Satıcı / Tedarikçi)",
        },
        "vendor_tax_id": {
            "type": "string",
            "description": "Vendor tax ID / VKN / TCKN (Vergi Kimlik No)",
        },
        "customer_name": {
            "type": "string",
            "description": "Name of the customer / buyer (Alıcı)",
        },
        "currency": {
            "type": "string",
            "description": "3-letter currency code: TRY, USD, EUR, GBP, etc.",
        },
        "subtotal": {
            "type": "number",
            "description": "Amount before tax (Ara Toplam / Net Tutar)",
        },
        "tax_amount": {
            "type": "number",
            "description": "Total tax / KDV amount (KDV Tutarı)",
        },
        "total_amount": {
            "type": "number",
            "description": "Grand total including tax (Genel Toplam)",
        },
        "vat_rate": {
            "type": "number",
            "description": "VAT / KDV percentage (e.g. 20 for 20%). Use the most common rate if multiple.",
        },
        "direction": {
            "type": "string",
            "description": "'incoming' = expense we received (gider faturası), 'outgoing' = income we issued (satış faturası)",
        },
        "category": {
            "type": "string",
            "description": f"One of: {', '.join(VALID_CATEGORIES)}",
        },
        "is_deductible": {
            "type": "boolean",
            "description": "true if this is a deductible expense (incoming invoice), false otherwise",
        },
        "line_items": {
            "type": "array",
            "description": (
                "Separate items, products or services in the invoice. "
                "Extract ALL line items! Each has its own name, quantity, price."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "item_name": {
                        "type": "string",
                        "description": "Product or service name (Mal/Hizmet Adı)",
                    },
                    "quantity": {
                        "type": "number",
                        "description": "Quantity (Miktar). Default 1 if not specified.",
                    },
                    "unit_price": {
                        "type": "number",
                        "description": "Price per unit before tax (Birim Fiyat)",
                    },
                    "total_price": {
                        "type": "number",
                        "description": "Total price for this line = quantity × unit_price (Tutar)",
                    },
                    "vat_rate": {
                        "type": "number",
                        "description": "VAT rate for this specific item (KDV %). 0 if exempt.",
                    },
                },
                "required": [
                    "item_name",
                    "quantity",
                    "unit_price",
                    "total_price",
                    "vat_rate",
                ],
            },
        },
        "confidence": {
            "type": "number",
            "description": "Your confidence in the extraction accuracy, 0.0 to 1.0",
        },
    },
    "required": [
        "invoice_number",
        "invoice_date",
        "vendor_name",
        "currency",
        "subtotal",
        "tax_amount",
        "total_amount",
        "vat_rate",
        "direction",
        "category",
        "is_deductible",
        "line_items",
        "confidence",
    ],
}

# ─── Extraction system prompt (TaxHacker-inspired) ──────────────────────────
EXTRACTION_SYSTEM = (
    "You are an expert invoice/receipt data extraction AI. "
    "You MUST respond with ONLY valid JSON that matches the provided schema. "
    "No explanation, no markdown, no backticks, no extra text. "
    "Just the raw JSON object."
)

EXTRACTION_PROMPT_TEMPLATE = """Extract structured data from this invoice/receipt document.

DOCUMENT TEXT:
{document_text}

FILE NAME: {file_name}

INSTRUCTIONS:
1. Extract ALL fields listed in the schema below.
2. Extract ALL line items — every product, service, or charge that appears as a separate row in the invoice.
3. Handle Turkish invoices: KDV = VAT, Fatura = Invoice, Toplam = Total, Ara Toplam = Subtotal.
4. Handle multiple currencies: look for TRY (₺), USD ($), EUR (€), GBP (£).
5. For direction: 'incoming' = this is an expense/bill we received; 'outgoing' = this is a sale/income we issued.
6. For category, use EXACTLY one of: {categories}
7. If a field is not found in the document, use null.
8. For dates, always use YYYY-MM-DD format.
9. For numbers, use plain numbers (no currency symbols, no thousands separators).
10. Estimate your confidence 0.0-1.0 based on text quality and completeness.

REQUIRED JSON SCHEMA:
{schema}

Respond with ONLY the JSON object. No explanation."""


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

    # ── LLM extraction (TaxHacker-inspired structured schema) ────────────────
    def extract_fields(self, raw_text: str, file_name: str = "") -> dict:
        """
        Extract structured invoice data using a strict JSON schema prompt.

        Sends the document text + a full JSON Schema description to Ollama,
        mirroring TaxHacker's `fieldsToJsonSchema()` + `buildLLMPrompt()`
        approach. The schema requires line_items extraction so every
        product/service row is captured individually.
        """
        if not raw_text or len(raw_text.strip()) < 20:
            return {"error": "Insufficient text extracted"}

        prompt = EXTRACTION_PROMPT_TEMPLATE.format(
            document_text=raw_text[:4000],
            file_name=file_name,
            categories=", ".join(VALID_CATEGORIES),
            schema=json.dumps(EXTRACTION_SCHEMA, indent=2),
        )

        result = call_ollama_json(
            prompt,
            # The schema_example for call_ollama_json's fallback regex parser.
            # This is a simpler flat example; the real schema is in the prompt.
            schema_example={
                "invoice_number": "INV-001",
                "invoice_date": "2024-01-15",
                "vendor_name": "Example Co",
                "currency": "TRY",
                "subtotal": 1000.0,
                "tax_amount": 200.0,
                "total_amount": 1200.0,
                "vat_rate": 20,
                "direction": "incoming",
                "category": "software",
                "is_deductible": True,
                "line_items": [
                    {
                        "item_name": "Product A",
                        "quantity": 1,
                        "unit_price": 1000.0,
                        "total_price": 1000.0,
                        "vat_rate": 20,
                    }
                ],
                "confidence": 0.85,
            },
            task=TaskType.REASONING,
            timeout=120,
        )

        # Validate and normalize the response
        if not result or not isinstance(result, dict):
            return {"error": "LLM returned invalid response"}

        # Normalize category to a valid value
        cat = (result.get("category") or "other").lower().strip()
        if cat not in VALID_CATEGORIES:
            # Try to map legacy categories
            cat_map = {
                "marketing": "advertising",
                "professional_services": "services",
                "hardware": "products",
                "rent": "utilities",
                "food": "other",
                "food_basic": "other",
                "food_processed": "other",
                "general": "other",
            }
            cat = cat_map.get(cat, "other")
        result["category"] = cat

        # Ensure line_items is always a list
        items = result.get("line_items")
        if not isinstance(items, list):
            result["line_items"] = []

        # Validate each line item has required fields
        valid_items: list[dict] = []
        for item in result.get("line_items", []):
            if isinstance(item, dict) and item.get("item_name"):
                valid_items.append(
                    {
                        "item_name": str(item.get("item_name", "")),
                        "quantity": float(item.get("quantity", 1) or 1),
                        "unit_price": float(item.get("unit_price", 0) or 0),
                        "total_price": float(item.get("total_price", 0) or 0),
                        "vat_rate": float(item.get("vat_rate", 0) or 0),
                    }
                )
        result["line_items"] = valid_items

        return result

    # ── Tax logic (Turkey) ───────────────────────────────────────────────────
    def classify_tax(self, data: dict) -> dict:
        category = data.get("category") or "other"
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
        items = invoice.get("line_items") or []
        items_summary = ""
        if items:
            items_summary = f"\nLine items ({len(items)}): " + ", ".join(
                f"{it.get('item_name', '?')} ({it.get('quantity', 1)}x "
                f"{it.get('unit_price', 0):.2f})"
                for it in items[:5]
            )
            if len(items) > 5:
                items_summary += f" ... and {len(items) - 5} more"

        prompt = f"""You are an accounting assistant. Brief practical insight for this invoice.
Vendor: {invoice.get('vendor_name')} | Date: {invoice.get('invoice_date')}
Amount: {invoice.get('total_amount')} {invoice.get('currency', 'TRY')} | VAT: {tax.get('vat_amount')} ({tax.get('vat_rate')}%)
Type: {invoice.get('direction', 'incoming')} | Category: {invoice.get('category')}{items_summary}
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
