"""
CRM Integration — Powered by Twenty CRM
Free, open-source Salesforce alternative.

Twenty uses GraphQL API at /graphql endpoint.
Connects growth data to customer relationships.
"""

import os
import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/v1/crm", tags=["crm"])

# Twenty runs on host port 3333; from inside Docker use host.docker.internal
TWENTY_URL = os.getenv("TWENTY_URL", "http://host.docker.internal:3333")


def _api_key() -> str:
    return os.getenv("TWENTY_API_KEY", "")


async def graphql(query: str, variables: dict = None) -> dict:
    """Execute a GraphQL query against Twenty CRM."""
    key = _api_key()
    if not key:
        return {"errors": [{"message": "TWENTY_API_KEY not configured"}]}
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{TWENTY_URL}/graphql",
                headers=headers,
                json={"query": query, "variables": variables or {}},
            )
            if resp.status_code == 200:
                return resp.json()
            return {"errors": [{"message": f"HTTP {resp.status_code}: {resp.text[:200]}"}]}
    except Exception as e:
        return {"errors": [{"message": str(e)}]}


# ─── Models ───────────────────────────────────────────────────────────────────

class PersonCreate(BaseModel):
    name: str
    email: Optional[str] = ""
    company: Optional[str] = ""
    source: Optional[str] = "organic"


class CompanyCreate(BaseModel):
    name: str
    domain: Optional[str] = ""
    industry: Optional[str] = ""


# ─── Health ───────────────────────────────────────────────────────────────────

@router.get("/health")
async def check_health():
    """Check if Twenty CRM is configured and reachable."""
    if not _api_key():
        return {
            "status": "not_configured",
            "twenty_url": "http://localhost:3333",
            "action": "Go to Twenty → Settings → API → Generate API Key, then add TWENTY_API_KEY to .env",
        }
    # Try reachability first
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{TWENTY_URL}/healthz")
            if r.status_code not in (200, 404):
                return {"status": "offline", "twenty_url": "http://localhost:3333", "hint": "cd apps/twenty && docker compose up -d"}
    except Exception:
        return {"status": "offline", "twenty_url": "http://localhost:3333", "hint": "cd apps/twenty && docker compose up -d"}

    result = await graphql("{ people(filter: {}) { totalCount } }")
    if "errors" not in result:
        return {
            "status": "connected",
            "twenty_url": "http://localhost:3333",
        }
    return {"status": "error", "details": result.get("errors"), "twenty_url": "http://localhost:3333"}


@router.get("/stats/overview")
async def get_crm_overview():
    """Get CRM overview statistics."""
    people = await graphql("query { people(filter: {}) { totalCount } }")
    companies = await graphql("query { companies(filter: {}) { totalCount } }")
    opps = await graphql("query { opportunities(filter: {}) { totalCount } }")

    return {
        "total_contacts": people.get("data", {}).get("people", {}).get("totalCount", 0),
        "total_companies": companies.get("data", {}).get("companies", {}).get("totalCount", 0),
        "total_opportunities": opps.get("data", {}).get("opportunities", {}).get("totalCount", 0),
        "twenty_url": "http://localhost:3333",
        "status": "connected" if _api_key() else "not_configured",
    }


# ─── Contacts (People) ────────────────────────────────────────────────────────

@router.get("/contacts")
async def list_contacts(limit: int = 50):
    """List all CRM contacts."""
    query = """
    query($first: Int) {
        people(first: $first, orderBy: { createdAt: DescNullsLast }) {
            edges {
                node {
                    id
                    name { firstName lastName }
                    emails { primaryEmail }
                    company { name }
                    createdAt
                }
            }
            totalCount
        }
    }"""

    result = await graphql(query, {"first": limit})
    if "errors" in result:
        return {"error": result["errors"], "contacts": [], "total": 0}

    edges = result.get("data", {}).get("people", {}).get("edges", [])
    contacts = []
    for edge in edges:
        node = edge.get("node", {})
        name = node.get("name", {})
        contacts.append({
            "id": node.get("id"),
            "name": f"{name.get('firstName', '')} {name.get('lastName', '')}".strip(),
            "email": node.get("emails", {}).get("primaryEmail", ""),
            "company": (node.get("company") or {}).get("name", ""),
            "created": node.get("createdAt", ""),
        })

    return {
        "total": result.get("data", {}).get("people", {}).get("totalCount", 0),
        "contacts": contacts,
    }


@router.post("/contacts")
async def create_contact(person: PersonCreate):
    """Add a new contact to Twenty CRM."""
    names = person.name.split(" ", 1)
    first = names[0]
    last = names[1] if len(names) > 1 else ""

    mutation = """
    mutation CreatePerson($data: PersonCreateInput!) {
        createPerson(data: $data) {
            id
            name { firstName lastName }
            emails { primaryEmail }
        }
    }"""

    data: dict = {"name": {"firstName": first, "lastName": last}}
    if person.email:
        data["emails"] = {"primaryEmail": person.email}

    result = await graphql(mutation, {"data": data})
    if "errors" in result:
        return {"success": False, "error": result["errors"]}

    created = result.get("data", {}).get("createPerson", {})
    cid = created.get("id")
    return {
        "success": bool(cid),
        "id": cid,
        "name": person.name,
        "email": person.email,
        "twenty_url": f"http://localhost:3333/objects/people/{cid}" if cid else "http://localhost:3333",
    }


# ─── Companies ────────────────────────────────────────────────────────────────

@router.get("/companies")
async def list_companies(limit: int = 50):
    """List all companies in CRM."""
    query = """
    query($first: Int) {
        companies(first: $first, orderBy: { createdAt: DescNullsLast }) {
            edges {
                node {
                    id
                    name
                    domainName { primaryLinkUrl }
                    employees
                    createdAt
                }
            }
            totalCount
        }
    }"""

    result = await graphql(query, {"first": limit})
    if "errors" in result:
        return {"error": result["errors"], "companies": [], "total": 0}

    edges = result.get("data", {}).get("companies", {}).get("edges", [])
    companies = [
        {
            "id": e["node"]["id"],
            "name": e["node"]["name"],
            "domain": (e["node"].get("domainName") or {}).get("primaryLinkUrl", ""),
            "employees": e["node"].get("employees"),
            "created": e["node"].get("createdAt"),
        }
        for e in edges
    ]

    return {
        "total": result.get("data", {}).get("companies", {}).get("totalCount", 0),
        "companies": companies,
    }


@router.post("/companies")
async def create_company(company: CompanyCreate):
    """Create a new company in Twenty CRM."""
    mutation = """
    mutation CreateCompany($data: CompanyCreateInput!) {
        createCompany(data: $data) {
            id
            name
        }
    }"""

    data: dict = {"name": company.name}
    if company.domain:
        data["domainName"] = {"primaryLinkUrl": company.domain}

    result = await graphql(mutation, {"data": data})
    if "errors" in result:
        return {"success": False, "error": result["errors"]}

    created = result.get("data", {}).get("createCompany", {})
    cid = created.get("id")
    return {
        "success": bool(cid),
        "id": cid,
        "name": company.name,
        "twenty_url": f"http://localhost:3333/objects/companies/{cid}" if cid else "http://localhost:3333",
    }


# ─── Opportunities (Deals) ────────────────────────────────────────────────────

@router.get("/opportunities")
async def list_opportunities(limit: int = 50):
    """List all deals/opportunities."""
    query = """
    query($first: Int) {
        opportunities(first: $first, orderBy: { createdAt: DescNullsLast }) {
            edges {
                node {
                    id
                    name
                    amount { amountMicros currencyCode }
                    stage
                    closeDate
                    createdAt
                }
            }
            totalCount
        }
    }"""

    result = await graphql(query, {"first": limit})
    if "errors" in result:
        return {"error": result["errors"], "opportunities": [], "total": 0}

    edges = result.get("data", {}).get("opportunities", {}).get("edges", [])
    deals = []
    for e in edges:
        node = e["node"]
        amount = node.get("amount") or {}
        deals.append({
            "id": node["id"],
            "name": node["name"],
            "amount": (amount.get("amountMicros", 0) or 0) / 1_000_000,
            "currency": amount.get("currencyCode", "USD"),
            "stage": node.get("stage"),
            "close_date": node.get("closeDate"),
            "created": node.get("createdAt"),
        })

    return {
        "total": result.get("data", {}).get("opportunities", {}).get("totalCount", 0),
        "opportunities": deals,
    }


# ─── Growth → CRM Sync ────────────────────────────────────────────────────────

@router.post("/sync/from-outreach")
async def sync_outreach_to_crm(
    prospect_name: str,
    prospect_email: str,
    prospect_company: str,
    outreach_channel: str,
    source: str = "outreach",
):
    """
    When outreach is sent via Growth Intelligence,
    automatically create the prospect in Twenty CRM.
    """
    company_result = await create_company(CompanyCreate(name=prospect_company))
    person_result = await create_contact(
        PersonCreate(name=prospect_name, email=prospect_email, company=prospect_company, source=source)
    )

    cid = person_result.get("id")
    return {
        "success": bool(cid),
        "contact_id": cid,
        "company_id": company_result.get("id"),
        "twenty_contact_url": f"http://localhost:3333/objects/people/{cid}" if cid else "http://localhost:3333",
        "channel": outreach_channel,
    }
