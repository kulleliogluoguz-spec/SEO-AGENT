"""
Workflow Automation Engine — Powered by n8n
Connects all platform features into automated pipelines.

n8n runs at: http://localhost:5678 (host) / http://host.docker.internal:5678 (from container)
n8n API: http://host.docker.internal:5678/api/v1/

Pre-built workflows:
1. New Contact → Mautic + Welcome Email
2. Content Generated → Auto-score + Post if score >80
3. Weekly Scorecard → Auto-generate every Monday
"""

import os
import base64
import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict

router = APIRouter(prefix="/api/v1/workflows", tags=["workflow-automation"])

# n8n is on host port 5678; from inside Docker use host.docker.internal
N8N_URL = os.getenv("N8N_URL", "http://host.docker.internal:5678")
N8N_USER = os.getenv("N8N_USER", "admin")
N8N_PASS = os.getenv("N8N_PASS", "Admin1234!")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")

# Our API is only reachable via nginx port 80 on the host
_API_BASE = "http://host.docker.internal/api/v1"


async def n8n_request(method: str, endpoint: str, data: dict = None) -> dict:
    """Authenticated request to n8n REST API."""
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if N8N_API_KEY:
        headers["X-N8N-API-KEY"] = N8N_API_KEY
    else:
        creds = base64.b64encode(f"{N8N_USER}:{N8N_PASS}".encode()).decode()
        headers["Authorization"] = f"Basic {creds}"

    url = f"{N8N_URL}/api/v1/{endpoint}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                resp = await client.get(url, headers=headers)
            elif method == "POST":
                resp = await client.post(url, headers=headers, json=data or {})
            elif method == "DELETE":
                resp = await client.delete(url, headers=headers)
            else:
                return {"error": f"Unknown method: {method}"}

            if resp.status_code in [200, 201]:
                return resp.json()
            return {"error": resp.text[:500], "status": resp.status_code}
    except Exception as e:
        return {"error": str(e), "n8n_url": N8N_URL}


async def trigger_webhook(webhook_path: str, data: dict) -> dict:
    """Trigger an n8n webhook workflow."""
    url = f"{N8N_URL}/webhook/{webhook_path}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=data)
            if resp.status_code in [200, 201]:
                return {"triggered": True, "response": resp.json() if resp.text else {}}
            return {"triggered": False, "status": resp.status_code, "body": resp.text[:200]}
    except Exception as e:
        return {"triggered": False, "error": str(e)}


# ─── Models ───────────────────────────────────────────────────────────────────

class WorkflowTrigger(BaseModel):
    workflow_name: str
    data: Dict


class AutomationRule(BaseModel):
    name: str
    trigger: str
    condition: Optional[str] = ""
    actions: List[str]
    enabled: bool = True


# ─── Health & Status ──────────────────────────────────────────────────────────

@router.get("/health")
async def check_n8n_health():
    """Check if n8n is running and reachable."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{N8N_URL}/healthz")
            if resp.status_code == 200:
                return {"status": "connected", "n8n_url": N8N_URL}
    except Exception:
        pass
    return {
        "status": "offline",
        "n8n_url": N8N_URL,
        "hint": "Run: cd apps/n8n && docker compose up -d",
    }


@router.get("/overview")
async def get_overview():
    """Get all workflows and their status."""
    result = await n8n_request("GET", "workflows")
    workflows = result.get("data", [])
    return {
        "total_workflows": len(workflows),
        "active_workflows": len([w for w in workflows if w.get("active")]),
        "workflows": [
            {
                "id": w.get("id"),
                "name": w.get("name"),
                "active": w.get("active"),
                "created": w.get("createdAt"),
            }
            for w in workflows
        ],
        "n8n_editor": "http://localhost:5678",
        "status": "connected" if "data" in result else "error",
    }


# ─── Pre-built Workflows ──────────────────────────────────────────────────────

@router.post("/setup/contact-automation")
async def setup_contact_automation():
    """Create workflow: New Contact → Add to Mautic → Send Welcome Email."""
    workflow = {
        "name": "New Contact → Mautic + Welcome Email",
        "settings": {},
        "nodes": [
            {
                "id": "webhook-trigger",
                "name": "New Contact Webhook",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [250, 300],
                "parameters": {
                    "path": "new-contact",
                    "responseMode": "onReceived",
                    "httpMethod": "POST",
                },
            },
            {
                "id": "http-mautic",
                "name": "Add to Mautic",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 3,
                "position": [500, 300],
                "parameters": {
                    "method": "POST",
                    "url": f"{_API_BASE}/email/contacts",
                    "sendBody": True,
                    "contentType": "json",
                    "body": '={"email":"{{$json.email}}","firstname":"{{$json.firstname}}","business_type":"{{$json.business_type}}"}',
                },
            },
            {
                "id": "wait-node",
                "name": "Wait 1 Minute",
                "type": "n8n-nodes-base.wait",
                "typeVersion": 1,
                "position": [750, 300],
                "parameters": {"unit": "minutes", "amount": 1},
            },
            {
                "id": "http-sequence",
                "name": "Trigger Welcome Sequence",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 3,
                "position": [1000, 300],
                "parameters": {
                    "method": "POST",
                    "url": f"{_API_BASE}/email/sequences/generate",
                    "sendBody": True,
                    "contentType": "json",
                    "body": '={"name":"Welcome - {{$json.email}}","business_type":"{{$json.business_type || \'saas\'}}","sequence_type":"welcome"}',
                },
            },
        ],
        "connections": {
            "New Contact Webhook": {
                "main": [[{"node": "Add to Mautic", "type": "main", "index": 0}]]
            },
            "Add to Mautic": {
                "main": [[{"node": "Wait 1 Minute", "type": "main", "index": 0}]]
            },
            "Wait 1 Minute": {
                "main": [[{"node": "Trigger Welcome Sequence", "type": "main", "index": 0}]]
            },
        },
    }

    result = await n8n_request("POST", "workflows", workflow)
    workflow_id = result.get("id")
    return {
        "success": bool(workflow_id),
        "workflow_id": workflow_id,
        "workflow_name": "New Contact → Mautic + Welcome Email",
        "webhook_url": "http://localhost:5678/webhook/new-contact",
        "test_command": 'curl -X POST http://localhost:5678/webhook/new-contact -H "Content-Type: application/json" -d \'{"email":"test@example.com","firstname":"Test","business_type":"saas"}\'',
        "n8n_url": f"http://localhost:5678/workflow/{workflow_id}" if workflow_id else "http://localhost:5678",
    }


@router.post("/setup/content-auto-score")
async def setup_content_auto_score():
    """Create workflow: Content Generated → Auto-score → Post if score >80."""
    workflow = {
        "name": "Content Generated → Auto-score → Post if >80",
        "settings": {},
        "nodes": [
            {
                "id": "webhook-trigger",
                "name": "Content Generated Webhook",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [250, 300],
                "parameters": {
                    "path": "content-generated",
                    "responseMode": "onReceived",
                    "httpMethod": "POST",
                },
            },
            {
                "id": "score-content",
                "name": "Score Content",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 3,
                "position": [500, 300],
                "parameters": {
                    "method": "POST",
                    "url": f"{_API_BASE}/intelligence/content/score",
                    "sendBody": True,
                    "contentType": "json",
                    "body": '={"content":"{{$json.content}}","content_type":"{{$json.content_type || \'tweet\'}}","target_audience":"{{$json.target_audience || \'general\'}}","goal":"engagement","business_type":"{{$json.business_type || \'saas\'}}"}',
                },
            },
            {
                "id": "check-score",
                "name": "Check Score > 80",
                "type": "n8n-nodes-base.if",
                "typeVersion": 1,
                "position": [750, 300],
                "parameters": {
                    "conditions": {
                        "number": [
                            {
                                "value1": "={{$json.overall_score}}",
                                "operation": "larger",
                                "value2": 80,
                            }
                        ]
                    }
                },
            },
        ],
        "connections": {
            "Content Generated Webhook": {
                "main": [[{"node": "Score Content", "type": "main", "index": 0}]]
            },
            "Score Content": {
                "main": [[{"node": "Check Score > 80", "type": "main", "index": 0}]]
            },
        },
    }

    result = await n8n_request("POST", "workflows", workflow)
    return {
        "success": "id" in result,
        "workflow_id": result.get("id"),
        "webhook_url": "http://localhost:5678/webhook/content-generated",
        "n8n_url": f"http://localhost:5678/workflow/{result.get('id')}" if result.get("id") else "http://localhost:5678",
    }


@router.post("/setup/weekly-scorecard")
async def setup_weekly_scorecard():
    """Create workflow: Every Monday 9am → Generate weekly scorecard."""
    workflow = {
        "name": "Weekly Growth Scorecard — Every Monday",
        "settings": {},
        "nodes": [
            {
                "id": "schedule",
                "name": "Every Monday 9am",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1,
                "position": [250, 300],
                "parameters": {
                    "rule": {
                        "interval": [
                            {"field": "cronExpression", "expression": "0 9 * * 1"}
                        ]
                    }
                },
            },
            {
                "id": "generate-scorecard",
                "name": "Generate Scorecard",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 3,
                "position": [500, 300],
                "parameters": {
                    "method": "POST",
                    "url": f"{_API_BASE}/intelligence/scorecard/weekly",
                    "sendBody": True,
                    "contentType": "json",
                    "body": '{"business_type":"saas","niche":"marketing automation","metrics":{"website_visitors":0,"new_followers":0}}',
                },
            },
        ],
        "connections": {
            "Every Monday 9am": {
                "main": [[{"node": "Generate Scorecard", "type": "main", "index": 0}]]
            }
        },
    }

    result = await n8n_request("POST", "workflows", workflow)
    return {
        "success": "id" in result,
        "workflow_id": result.get("id"),
        "schedule": "Every Monday at 9:00 AM",
        "n8n_url": f"http://localhost:5678/workflow/{result.get('id')}" if result.get("id") else "http://localhost:5678",
    }


@router.post("/setup/all")
async def setup_all_workflows():
    """Setup ALL pre-built workflows at once."""
    results = {
        "contact_automation": await setup_contact_automation(),
        "content_auto_score": await setup_content_auto_score(),
        "weekly_scorecard": await setup_weekly_scorecard(),
    }
    successful = sum(1 for r in results.values() if r.get("success"))
    return {
        "workflows_created": successful,
        "total_attempted": len(results),
        "results": results,
        "n8n_editor": "http://localhost:5678",
        "next_step": "Open http://localhost:5678 to see and activate your workflows",
    }


# ─── Manual Triggers ─────────────────────────────────────────────────────────

@router.post("/trigger/new-contact")
async def trigger_new_contact(email: str, firstname: str = "", business_type: str = "saas"):
    """Manually trigger the new contact workflow."""
    return await trigger_webhook("new-contact", {
        "email": email,
        "firstname": firstname,
        "business_type": business_type,
    })


@router.post("/trigger/content-score")
async def trigger_content_score(content: str, content_type: str = "tweet", business_type: str = "saas"):
    """Manually trigger the content scoring workflow."""
    return await trigger_webhook("content-generated", {
        "content": content,
        "content_type": content_type,
        "business_type": business_type,
    })


@router.get("/executions")
async def get_recent_executions(limit: int = 20):
    """Get recent workflow execution history."""
    result = await n8n_request("GET", f"executions?limit={limit}&includeData=false")
    executions = result.get("data", [])
    return {
        "total": len(executions),
        "executions": [
            {
                "id": e.get("id"),
                "workflow_name": e.get("workflowData", {}).get("name", "Unknown"),
                "status": e.get("status"),
                "started": e.get("startedAt"),
                "finished": e.get("stoppedAt"),
            }
            for e in executions
        ],
    }
