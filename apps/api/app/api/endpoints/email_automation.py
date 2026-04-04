"""
Email Automation Engine — Powered by Mautic
Replaces HubSpot/Mailchimp with 100% free, self-hosted solution.

Supports: e-commerce, SaaS, local business, personal brand
AI generation uses local Ollama qwen3:8b — zero external API cost
"""

import base64
import json
import logging
import os

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

load_dotenv()  # Load .env into os.environ so os.getenv picks up file values

router = APIRouter(prefix="/api/v1/email", tags=["email-automation"])

MAUTIC_URL = os.getenv("MAUTIC_URL", "http://localhost:8181")
MAUTIC_USER = os.getenv("MAUTIC_ADMIN_EMAIL", "admin@aicmo.os")
MAUTIC_PASS = os.getenv("MAUTIC_ADMIN_PASSWORD", "Admin1234!")


async def mautic(method: str, endpoint: str, data: dict = None) -> dict:
    credentials = base64.b64encode(f"{MAUTIC_USER}:{MAUTIC_PASS}".encode()).decode()
    headers = {"Authorization": f"Basic {credentials}", "Content-Type": "application/json"}
    url = f"{MAUTIC_URL}/api/{endpoint}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                resp = await client.get(url, headers=headers)
            elif method == "POST":
                resp = await client.post(url, headers=headers, json=data or {})
            else:
                return {"error": f"Unsupported method: {method}"}
            if resp.status_code in [200, 201]:
                return resp.json()
            return {"error": resp.text, "status": resp.status_code}
    except Exception as e:
        return {"error": str(e)}


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
LLM_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")


async def ask_ollama(prompt: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": LLM_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 2048},
                    "think": False,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("response", "").strip()
                if not text:
                    logger.error(
                        "ask_ollama: empty response from model=%s, error=%s",
                        LLM_MODEL,
                        data.get("error"),
                    )
                return text
            logger.error("ask_ollama: status=%d body=%s", resp.status_code, resp.text[:300])
    except Exception as e:
        logger.error("ask_ollama failed: %s", e)
        return ""
    return ""


def extract_json(text: str) -> dict:
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception:
        pass
    return {}


class ContactCreate(BaseModel):
    email: str
    firstname: str | None = ""
    lastname: str | None = ""
    company: str | None = ""
    business_type: str | None = ""
    tags: list[str] | None = []


class SequenceRequest(BaseModel):
    name: str
    business_type: str
    sequence_type: str  # welcome | abandoned_cart | re_engagement | nurture | onboarding
    niche: str | None = ""


@router.get("/health")
async def check_health():
    result = await mautic("GET", "contacts?limit=1")
    if "error" not in result:
        return {"status": "connected", "mautic_url": MAUTIC_URL}
    return {"status": "error", "details": result.get("error"), "mautic_url": MAUTIC_URL}


@router.get("/stats/overview")
async def get_overview():
    contacts_res = await mautic("GET", "contacts?limit=1")
    campaigns_res = await mautic("GET", "campaigns?limit=100")
    emails_res = await mautic("GET", "emails?limit=100")
    campaigns = (
        list(campaigns_res.get("campaigns", {}).values())
        if isinstance(campaigns_res.get("campaigns"), dict)
        else []
    )
    emails = (
        list(emails_res.get("emails", {}).values())
        if isinstance(emails_res.get("emails"), dict)
        else []
    )
    return {
        "total_contacts": contacts_res.get("total", 0),
        "total_campaigns": len(campaigns),
        "total_emails": len(emails),
        "active_campaigns": len([c for c in campaigns if c.get("isPublished")]),
        "mautic_dashboard": f"{MAUTIC_URL}/s/dashboard",
        "status": "connected",
    }


@router.get("/contacts")
async def list_contacts(limit: int = 50, search: str = ""):
    endpoint = f"contacts?limit={limit}"
    if search:
        endpoint += f"&search={search}"
    result = await mautic("GET", endpoint)
    contacts = (
        list(result.get("contacts", {}).values())
        if isinstance(result.get("contacts"), dict)
        else []
    )
    return {"total": result.get("total", len(contacts)), "contacts": contacts}


@router.post("/contacts")
async def create_contact(contact: ContactCreate):
    # Mautic API does not accept 'tags' in the contact creation payload — create first, tag separately
    data = {
        "email": contact.email,
        "firstname": contact.firstname,
        "lastname": contact.lastname,
        "company": contact.company,
    }
    result = await mautic("POST", "contacts/new", data)
    # Apply tag via a separate call if contact was created successfully
    contact_id = result.get("contact", {}).get("id") if "contact" in result else None
    tags = list(contact.tags or [])
    if contact.business_type:
        tags.append(contact.business_type)
    if contact_id and tags:
        for tag in tags:
            await mautic("POST", f"contacts/{contact_id}/tags/add", {"tags": [tag]})
    return result


@router.post("/sequences/generate")
async def generate_sequence(req: SequenceRequest):
    """Use Ollama AI to generate a complete email sequence, then create all emails in Mautic."""
    prompts = {
        "welcome": f"""Write a 5-email welcome sequence for a {req.business_type} business in the {req.niche or 'general'} niche.
Emails sent on days: 0, 1, 3, 7, 14. Personal, value-first tone. Not salesy.
Respond ONLY with valid JSON:
{{"sequence_name":"Welcome Series","emails":[
  {{"day":0,"subject":"...","preview_text":"...","body":"<p>email body</p>","goal":"introduce brand"}},
  {{"day":1,"subject":"...","preview_text":"...","body":"<p>email body</p>","goal":"deliver value"}},
  {{"day":3,"subject":"...","preview_text":"...","body":"<p>email body</p>","goal":"educate"}},
  {{"day":7,"subject":"...","preview_text":"...","body":"<p>email body</p>","goal":"social proof"}},
  {{"day":14,"subject":"...","preview_text":"...","body":"<p>email body</p>","goal":"soft offer"}}
]}}""",
        "abandoned_cart": f"""Write a 3-email abandoned cart sequence for {req.business_type} in {req.niche or 'e-commerce'}.
Sent at: 1 hour, 24 hours, 72 hours after abandonment.
Respond ONLY with valid JSON:
{{"sequence_name":"Cart Recovery","emails":[
  {{"delay_hours":1,"subject":"...","preview_text":"...","body":"<p>...</p>","discount":"none"}},
  {{"delay_hours":24,"subject":"...","preview_text":"...","body":"<p>...</p>","discount":"5%"}},
  {{"delay_hours":72,"subject":"...","preview_text":"...","body":"<p>...</p>","discount":"10%"}}
]}}""",
        "re_engagement": f"""Write a 4-email re-engagement sequence for {req.business_type} customers inactive 30 days.
Respond ONLY with valid JSON:
{{"sequence_name":"Win-Back Campaign","emails":[
  {{"day":0,"subject":"We miss you...","preview_text":"...","body":"<p>...</p>"}},
  {{"day":3,"subject":"...","preview_text":"...","body":"<p>...</p>"}},
  {{"day":7,"subject":"...","preview_text":"...","body":"<p>...</p>"}},
  {{"day":14,"subject":"Last chance...","preview_text":"...","body":"<p>...</p>"}}
]}}""",
        "nurture": f"""Write a 6-email lead nurture sequence for {req.niche or req.business_type}.
Respond ONLY with valid JSON:
{{"sequence_name":"Lead Nurture","emails":[
  {{"day":0,"subject":"...","preview_text":"...","body":"<p>...</p>","content_type":"educational"}},
  {{"day":2,"subject":"...","preview_text":"...","body":"<p>...</p>","content_type":"case_study"}},
  {{"day":5,"subject":"...","preview_text":"...","body":"<p>...</p>","content_type":"tips"}},
  {{"day":8,"subject":"...","preview_text":"...","body":"<p>...</p>","content_type":"social_proof"}},
  {{"day":12,"subject":"...","preview_text":"...","body":"<p>...</p>","content_type":"offer"}},
  {{"day":16,"subject":"...","preview_text":"...","body":"<p>...</p>","content_type":"urgency"}}
]}}""",
        "onboarding": f"""Write a 5-email onboarding sequence for new {req.business_type} users in {req.niche or 'SaaS'}.
Respond ONLY with valid JSON:
{{"sequence_name":"Onboarding","emails":[
  {{"day":0,"subject":"...","preview_text":"...","body":"<p>...</p>","action":"complete profile"}},
  {{"day":1,"subject":"...","preview_text":"...","body":"<p>...</p>","action":"first feature"}},
  {{"day":3,"subject":"...","preview_text":"...","body":"<p>...</p>","action":"key use case"}},
  {{"day":7,"subject":"...","preview_text":"...","body":"<p>...</p>","action":"advanced feature"}},
  {{"day":14,"subject":"...","preview_text":"...","body":"<p>...</p>","action":"upgrade or refer"}}
]}}""",
    }

    prompt = prompts.get(req.sequence_type, prompts["welcome"])
    ai_response = await ask_ollama(prompt)
    sequence_data = extract_json(ai_response)

    if not sequence_data:
        return {"error": "AI generation failed — is Ollama running?", "hint": "Run: ollama serve"}

    created_emails = []
    for i, email in enumerate(sequence_data.get("emails", [])):
        delay = email.get("day", email.get("delay_hours", i))
        delay_unit = "hours" if "delay_hours" in email else "days"
        email_data = {
            "name": f"{req.name} — {delay_unit[:-1].title()} {delay}",
            "subject": email.get("subject", f"Email {i + 1}"),
            "customHtml": email.get("body", "<p>Email content</p>"),
            "previewText": email.get("preview_text", ""),
            "emailType": "template",
            "isPublished": True,
        }
        result = await mautic("POST", "emails/new", email_data)
        mautic_id = result.get("email", {}).get("id") if "email" in result else None
        created_emails.append(
            {
                "position": i + 1,
                "mautic_id": mautic_id,
                "subject": email.get("subject"),
                "delay": f"{delay_unit[:-1]} {delay}",
                "goal": email.get("goal", email.get("content_type", email.get("action", ""))),
                "mautic_url": f"{MAUTIC_URL}/s/emails/{mautic_id}/edit" if mautic_id else None,
            }
        )

    return {
        "success": True,
        "sequence_name": sequence_data.get("sequence_name", req.name),
        "sequence_type": req.sequence_type,
        "emails_created": len(created_emails),
        "emails": created_emails,
        "next_steps": [
            f"1. Go to Mautic: {MAUTIC_URL}/s/campaigns",
            "2. Create a new Campaign",
            "3. Add these emails with correct delays",
            "4. Set trigger condition",
            "5. Publish the campaign",
        ],
        "mautic_emails_url": f"{MAUTIC_URL}/s/emails",
    }


@router.get("/campaigns")
async def list_campaigns():
    result = await mautic("GET", "campaigns")
    campaigns = (
        list(result.get("campaigns", {}).values())
        if isinstance(result.get("campaigns"), dict)
        else []
    )
    return {"campaigns": campaigns, "total": result.get("total", 0)}


@router.get("/emails")
async def list_emails():
    result = await mautic("GET", "emails")
    emails = (
        list(result.get("emails", {}).values()) if isinstance(result.get("emails"), dict) else []
    )
    return {
        "emails": emails,
        "total": result.get("total", 0),
        "manage_url": f"{MAUTIC_URL}/s/emails",
    }
