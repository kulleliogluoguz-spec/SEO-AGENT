"""
Twitter Autonomous Growth Engine — Multi-Account

Generates AI content daily using Ollama, manages a tweet queue,
posts approved tweets via X API v2 with OAuth 1.0a signing,
and tracks performance metrics.

Supports multiple connected X accounts stored in SQLite.
Falls back to .env credentials if no accounts are connected.
"""

import json
import logging
import os
import pathlib
import sqlite3
from datetime import datetime

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/twitter", tags=["twitter-engine"])

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

X_API_BASE = "https://api.twitter.com/2"

# ─── SQLite DB ────────────────────────────────────────────────────────────────

DB_PATH = pathlib.Path(__file__).resolve().parents[3] / "storage" / "twitter_queue.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tweet_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            tweet_type TEXT DEFAULT 'single',
            thread_tweets TEXT,
            status TEXT DEFAULT 'pending',
            niche TEXT DEFAULT '',
            hook_type TEXT DEFAULT '',
            pillar TEXT DEFAULT '',
            ai_score INTEGER DEFAULT 0,
            best_time TEXT DEFAULT '',
            account_id INTEGER,
            scheduled_for TEXT,
            posted_at TEXT,
            tweet_id TEXT,
            post_url TEXT,
            error_message TEXT,
            likes INTEGER DEFAULT 0,
            retweets INTEGER DEFAULT 0,
            replies INTEGER DEFAULT 0,
            impressions INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS twitter_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_id TEXT DEFAULT 'default',
            twitter_user_id TEXT,
            username TEXT,
            display_name TEXT DEFAULT '',
            access_token TEXT NOT NULL,
            access_token_secret TEXT NOT NULL,
            followers INTEGER DEFAULT 0,
            niche TEXT DEFAULT 'general',
            target_audience TEXT DEFAULT 'general audience',
            auto_generate INTEGER DEFAULT 1,
            connected_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()


_init_db()

# Auto-migrate: add missing columns to existing DBs
_MIGRATIONS = [
    ("tweet_queue", "account_id", "ALTER TABLE tweet_queue ADD COLUMN account_id INTEGER"),
    ("twitter_accounts", "niche", "ALTER TABLE twitter_accounts ADD COLUMN niche TEXT DEFAULT 'general'"),
    ("twitter_accounts", "target_audience", "ALTER TABLE twitter_accounts ADD COLUMN target_audience TEXT DEFAULT 'general audience'"),
    ("twitter_accounts", "auto_generate", "ALTER TABLE twitter_accounts ADD COLUMN auto_generate INTEGER DEFAULT 1"),
]
for _tbl, _col, _sql in _MIGRATIONS:
    try:
        _c = sqlite3.connect(DB_PATH)
        _c.execute(f"SELECT {_col} FROM {_tbl} LIMIT 1")
        _c.close()
    except sqlite3.OperationalError:
        _c = sqlite3.connect(DB_PATH)
        _c.execute(_sql)
        _c.commit()
        _c.close()


def _db(sql: str, params: tuple = (), *, fetch: bool = True):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(sql, params)
    if fetch:
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id


# ─── Account Credentials Helper ──────────────────────────────────────────────

def _get_account(account_id: int | None = None) -> dict | None:
    """Get account credentials from DB. Falls back to first active account, then .env."""
    if account_id:
        rows = _db("SELECT * FROM twitter_accounts WHERE id=? AND is_active=1", (account_id,))
        if rows:
            return rows[0]

    # Fall back to first active account
    rows = _db("SELECT * FROM twitter_accounts WHERE is_active=1 ORDER BY id LIMIT 1")
    if rows:
        return rows[0]

    # Fall back to .env
    api_key = os.getenv("X_API_KEY") or os.getenv("TWITTER_API_KEY")
    access_token = os.getenv("X_ACCESS_TOKEN") or os.getenv("TWITTER_ACCESS_TOKEN")
    access_secret = os.getenv("X_ACCESS_TOKEN_SECRET") or os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    if api_key and access_token and access_secret:
        return {
            "id": None,
            "access_token": access_token,
            "access_token_secret": access_secret,
            "username": "env",
            "twitter_user_id": None,
            "source": "env",
        }

    return None


def _build_auth_header(method: str, url: str, account: dict, query_params: dict | None = None) -> str:
    """Build OAuth 1.0a header for an account."""
    from app.core.config.settings import get_settings
    from app.core.security.oauth1 import build_auth_header

    s = get_settings()
    return build_auth_header(
        method=method,
        url=url,
        consumer_key=s.x_api_key,
        consumer_secret=s.x_api_secret,
        token=account["access_token"],
        token_secret=account["access_token_secret"],
        query_params=query_params,
    )


async def _verify_account(account: dict) -> dict | None:
    """Call GET /2/users/me to verify credentials and get user info."""
    url = f"{X_API_BASE}/users/me"
    qp = {"user.fields": "public_metrics,name"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                url,
                headers={"Authorization": _build_auth_header("GET", url, account, query_params=qp)},
                params=qp,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                metrics = data.get("public_metrics", {})
                return {
                    "twitter_user_id": data.get("id", ""),
                    "username": data.get("username", ""),
                    "display_name": data.get("name", ""),
                    "followers": metrics.get("followers_count", 0),
                }
            logger.warning("[x] verify_account got %s: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.error("Account verification failed: %s", e)
    return None


async def _post_to_x(text: str, account: dict, reply_to_id: str | None = None) -> dict:
    """Post a tweet via X API v2."""
    url = f"{X_API_BASE}/tweets"
    payload: dict = {"text": text[:280]}
    if reply_to_id:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to_id}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": _build_auth_header("POST", url, account),
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code == 201:
                data = resp.json().get("data", {})
                post_id = data.get("id", "")
                return {"success": True, "post_id": post_id, "post_url": f"https://x.com/i/web/status/{post_id}"}
            return {"success": False, "error": f"X API {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Ollama AI ────────────────────────────────────────────────────────────────

async def _ask_ollama(prompt: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            )
            if resp.status_code == 200:
                text = resp.json().get("response", "").strip()
                while "<think>" in text and "</think>" in text:
                    start = text.index("<think>")
                    end = text.index("</think>") + len("</think>")
                    text = text[:start] + text[end:]
                return text.strip()
    except Exception as e:
        logger.error("Ollama error: %s", e)
    return ""


def _extract_json(text: str) -> dict:
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except (json.JSONDecodeError, ValueError):
        pass
    return {}


# ─── Pydantic Models ─────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    niche: str
    target_audience: str
    content_pillars: list[str] | None = None
    count: int = 5
    include_threads: bool = True
    account_id: int | None = None


class ManualTweetRequest(BaseModel):
    content: str
    post_now: bool = False
    account_id: int | None = None


class EditTweetRequest(BaseModel):
    content: str


class ConnectAccountRequest(BaseModel):
    access_token: str
    access_token_secret: str
    workspace_id: str = "default"
    niche: str = "general"
    target_audience: str = "general audience"


class UpdateAccountRequest(BaseModel):
    niche: str | None = None
    target_audience: str | None = None
    auto_generate: bool | None = None


# ─── Account Management ──────────────────────────────────────────────────────

@router.post("/accounts/connect")
async def connect_account(req: ConnectAccountRequest):
    """Validate and store a new X account's access tokens."""
    account = {
        "access_token": req.access_token,
        "access_token_secret": req.access_token_secret,
    }
    info = await _verify_account(account)
    if not info:
        raise HTTPException(400, "Invalid credentials — could not authenticate with X API. Check your tokens and ensure app has Read+Write permissions.")

    # Check if this twitter user is already connected
    existing = _db(
        "SELECT id FROM twitter_accounts WHERE twitter_user_id=? AND is_active=1",
        (info["twitter_user_id"],),
    )
    if existing:
        # Update tokens for existing account
        _db(
            """UPDATE twitter_accounts
               SET access_token=?, access_token_secret=?, username=?,
                   display_name=?, followers=?, connected_at=?
               WHERE id=?""",
            (
                req.access_token, req.access_token_secret,
                info["username"], info["display_name"], info["followers"],
                datetime.now().isoformat(), existing[0]["id"],
            ),
            fetch=False,
        )
        return {
            "connected": True,
            "updated": True,
            "account": {
                "id": existing[0]["id"],
                "username": info["username"],
                "display_name": info["display_name"],
                "followers": info["followers"],
                "twitter_user_id": info["twitter_user_id"],
            },
        }

    account_id = _db(
        """INSERT INTO twitter_accounts
           (workspace_id, twitter_user_id, username, display_name,
            access_token, access_token_secret, followers, niche, target_audience, connected_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            req.workspace_id, info["twitter_user_id"], info["username"],
            info["display_name"], req.access_token, req.access_token_secret,
            info["followers"], req.niche, req.target_audience, datetime.now().isoformat(),
        ),
        fetch=False,
    )
    return {
        "connected": True,
        "account": {
            "id": account_id,
            "username": info["username"],
            "display_name": info["display_name"],
            "followers": info["followers"],
            "twitter_user_id": info["twitter_user_id"],
        },
    }


@router.get("/accounts")
async def list_accounts():
    """List all connected X accounts."""
    accounts = _db(
        "SELECT id, workspace_id, twitter_user_id, username, display_name, followers, niche, target_audience, auto_generate, connected_at, is_active FROM twitter_accounts WHERE is_active=1 ORDER BY id"
    )
    return {"accounts": accounts, "count": len(accounts)}


@router.delete("/accounts/{account_id}")
async def disconnect_account(account_id: int):
    """Disconnect (soft-delete) an X account."""
    rows = _db("SELECT id FROM twitter_accounts WHERE id=?", (account_id,))
    if not rows:
        raise HTTPException(404, "Account not found")
    _db("UPDATE twitter_accounts SET is_active=0 WHERE id=?", (account_id,), fetch=False)
    return {"disconnected": True, "id": account_id}


@router.get("/accounts/{account_id}/verify")
async def verify_account_endpoint(account_id: int):
    """Re-verify an account's credentials and update info."""
    rows = _db("SELECT * FROM twitter_accounts WHERE id=? AND is_active=1", (account_id,))
    if not rows:
        raise HTTPException(404, "Account not found")
    info = await _verify_account(rows[0])
    if not info:
        return {"valid": False, "message": "Credentials invalid or expired"}
    _db(
        "UPDATE twitter_accounts SET username=?, display_name=?, followers=? WHERE id=?",
        (info["username"], info["display_name"], info["followers"], account_id),
        fetch=False,
    )
    return {"valid": True, "account": {**info, "id": account_id}}


@router.put("/accounts/{account_id}")
async def update_account(account_id: int, req: UpdateAccountRequest):
    """Update account settings (niche, audience, auto-generate flag)."""
    rows = _db("SELECT id FROM twitter_accounts WHERE id=? AND is_active=1", (account_id,))
    if not rows:
        raise HTTPException(404, "Account not found")
    updates = []
    params: list = []
    if req.niche is not None:
        updates.append("niche=?")
        params.append(req.niche)
    if req.target_audience is not None:
        updates.append("target_audience=?")
        params.append(req.target_audience)
    if req.auto_generate is not None:
        updates.append("auto_generate=?")
        params.append(1 if req.auto_generate else 0)
    if updates:
        params.append(account_id)
        _db(f"UPDATE twitter_accounts SET {', '.join(updates)} WHERE id=?", tuple(params), fetch=False)
    return {"updated": True, "id": account_id}


# ─── Health & Stats ───────────────────────────────────────────────────────────

@router.get("/health")
async def twitter_health():
    """Return connection status. Does NOT call the X API (avoids rate limits).

    Checks in order:
    1. twitter_accounts table (populated by /accounts/connect or OAuth)
    2. credential_store (populated by OAuth callback)
    3. .env (X_ACCESS_TOKEN)
    """
    # 1. Check DB accounts — instant, no API call
    accounts = _db("SELECT * FROM twitter_accounts WHERE is_active=1 ORDER BY id")
    if accounts:
        return {
            "status": "connected",
            "message": f"{len(accounts)} account{'s' if len(accounts) != 1 else ''} connected",
            "accounts": [
                {
                    "id": acct["id"],
                    "username": acct["username"],
                    "display_name": acct.get("display_name", ""),
                    "followers": acct.get("followers", 0),
                    "valid": True,
                }
                for acct in accounts
            ],
        }

    # 2. Check credential_store (OAuth callback saves here)
    try:
        from app.core.store.credential_store import get_credential

        demo_uid = "00000000-0000-0000-0001-000000000001"
        cred = get_credential(demo_uid, "x") or get_credential(demo_uid, "twitter")
        if cred and cred.get("access_token"):
            extra = cred.get("extra") or {}
            username = extra.get("x_username", "")
            return {
                "status": "connected",
                "message": f"@{username} connected via OAuth" if username else "Token stored via OAuth",
                "accounts": [{
                    "id": None,
                    "username": username,
                    "display_name": "",
                    "followers": extra.get("followers", 0),
                    "valid": True,
                    "source": "oauth",
                }],
            }
    except Exception as e:
        logger.debug("[health] credential_store check failed: %s", e)

    # 3. Check .env
    access_token = os.getenv("X_ACCESS_TOKEN") or os.getenv("TWITTER_ACCESS_TOKEN")
    if access_token:
        return {
            "status": "connected",
            "message": "Token configured via .env",
            "accounts": [{
                "id": None,
                "username": "env",
                "display_name": "",
                "followers": 0,
                "valid": True,
                "source": "env",
            }],
        }

    return {
        "status": "not_configured",
        "message": "No X accounts connected",
        "accounts": [],
        "instructions": [
            "Connect your account in the dashboard below, or add tokens to .env:",
            "1. Go to developer.twitter.com > Your App > Keys and Tokens",
            "2. Generate Access Token & Secret (Read+Write permissions)",
            "3. Paste them in the 'Connect New Account' form below",
        ],
    }


@router.get("/stats")
async def twitter_stats():
    """Get queue and posting statistics."""
    pending = _db("SELECT COUNT(*) as c FROM tweet_queue WHERE status='pending'")[0]["c"]
    approved = _db("SELECT COUNT(*) as c FROM tweet_queue WHERE status='approved'")[0]["c"]
    posted = _db("SELECT COUNT(*) as c FROM tweet_queue WHERE status='posted'")[0]["c"]
    rejected = _db("SELECT COUNT(*) as c FROM tweet_queue WHERE status='rejected'")[0]["c"]
    errored = _db("SELECT COUNT(*) as c FROM tweet_queue WHERE status='error'")[0]["c"]

    month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
    this_month = _db(
        "SELECT COUNT(*) as c FROM tweet_queue WHERE status='posted' AND posted_at >= ?",
        (month_start,),
    )[0]["c"]

    total_likes = _db("SELECT COALESCE(SUM(likes),0) as s FROM tweet_queue WHERE status='posted'")[0]["s"]
    total_retweets = _db("SELECT COALESCE(SUM(retweets),0) as s FROM tweet_queue WHERE status='posted'")[0]["s"]
    total_impressions = _db("SELECT COALESCE(SUM(impressions),0) as s FROM tweet_queue WHERE status='posted'")[0]["s"]

    return {
        "queue": {
            "pending": pending,
            "approved": approved,
            "posted": posted,
            "rejected": rejected,
            "errored": errored,
        },
        "this_month_posts": this_month,
        "monthly_limit": 1500,
        "remaining_this_month": max(0, 1500 - this_month),
        "daily_safe_limit": 50,
        "totals": {
            "likes": total_likes,
            "retweets": total_retweets,
            "impressions": total_impressions,
        },
    }


# ─── Content Generation ───────────────────────────────────────────────────────

@router.post("/generate")
async def generate_tweets(req: GenerateRequest):
    """Generate a batch of tweets using Ollama AI and add to queue."""
    pillars = req.content_pillars or ["education", "opinion", "behind_scenes", "engagement"]

    prompt = f"""You are a viral Twitter/X content creator. Generate {req.count} tweets for a {req.niche} account targeting {req.target_audience}.

Content mix: {', '.join(pillars)}

Rules:
- Each tweet MUST be under 280 characters
- Use proven viral hooks: numbers, questions, contrarian takes, "hot take:", "unpopular opinion:"
- No hashtags in tweet body (max 1-2 at end if truly relevant)
- Conversational, human tone — not corporate
- Make people want to reply, retweet, or follow
{"- Also generate 1 thread (5 connected tweets)" if req.include_threads else ""}

Respond ONLY with valid JSON (no markdown, no explanation):
{{
    "tweets": [
        {{
            "content": "the tweet text (max 280 chars)",
            "hook_type": "question|stat|hot_take|story|tip|contrarian",
            "pillar": "education|opinion|engagement|behind_scenes",
            "ai_score": 85,
            "best_time": "9am|12pm|6pm|8pm"
        }}
    ]{"," if req.include_threads else ""}
    {"\"thread\": {" if req.include_threads else ""}
    {"    \"hook\": \"First tweet that hooks readers\"," if req.include_threads else ""}
    {"    \"tweets\": [\"1/ Hook...\", \"2/ ...\", \"3/ ...\", \"4/ ...\", \"5/ CTA...\"]," if req.include_threads else ""}
    {"    \"topic\": \"thread topic\"," if req.include_threads else ""}
    {"    \"ai_score\": 90" if req.include_threads else ""}
    {"}" if req.include_threads else ""}
}}"""

    response = await _ask_ollama(prompt)
    data = _extract_json(response)

    if not data:
        return {
            "error": "Generation failed — is Ollama running?",
            "hint": f"Run: ollama serve && ollama pull {OLLAMA_MODEL}",
            "generated": 0,
            "items": [],
        }

    added = []

    for tweet in data.get("tweets", []):
        content = tweet.get("content", "").strip()
        if not content or len(content) > 280:
            continue
        tweet_id = _db(
            """INSERT INTO tweet_queue
               (content, tweet_type, niche, hook_type, pillar, ai_score, best_time, account_id, status)
               VALUES (?, 'single', ?, ?, ?, ?, ?, ?, 'pending')""",
            (
                content,
                req.niche,
                tweet.get("hook_type", ""),
                tweet.get("pillar", ""),
                tweet.get("ai_score", 70),
                tweet.get("best_time", ""),
                req.account_id,
            ),
            fetch=False,
        )
        added.append({
            "id": tweet_id,
            "type": "single",
            "content": content,
            "hook_type": tweet.get("hook_type"),
            "pillar": tweet.get("pillar"),
            "ai_score": tweet.get("ai_score", 70),
            "best_time": tweet.get("best_time", ""),
            "status": "pending",
        })

    thread = data.get("thread")
    if thread and req.include_threads:
        thread_tweets = thread.get("tweets", [])
        hook = thread.get("hook", thread_tweets[0] if thread_tweets else "")
        thread_id = _db(
            """INSERT INTO tweet_queue
               (content, tweet_type, thread_tweets, niche, hook_type, pillar, ai_score, account_id, status)
               VALUES (?, 'thread', ?, ?, 'thread', 'education', ?, ?, 'pending')""",
            (hook, json.dumps(thread_tweets), req.niche, thread.get("ai_score", 85), req.account_id),
            fetch=False,
        )
        added.append({
            "id": thread_id,
            "type": "thread",
            "content": hook,
            "tweets_count": len(thread_tweets),
            "topic": thread.get("topic", ""),
            "ai_score": thread.get("ai_score", 85),
            "status": "pending",
        })

    return {
        "generated": len(added),
        "items": added,
        "message": f"{len(added)} items added to queue. Review and approve in the dashboard.",
    }


# ─── Queue Management ─────────────────────────────────────────────────────────

@router.get("/queue")
async def get_queue(status: str = "pending", limit: int = 50):
    """Get tweet queue by status: pending | approved | posted | rejected | error."""
    items = _db(
        "SELECT * FROM tweet_queue WHERE status=? ORDER BY ai_score DESC, created_at DESC LIMIT ?",
        (status, limit),
    )
    for item in items:
        if item.get("thread_tweets"):
            try:
                item["thread_tweets"] = json.loads(item["thread_tweets"])
            except (json.JSONDecodeError, TypeError):
                pass
    return {"status": status, "count": len(items), "items": items}


@router.get("/queue/{tweet_id}")
async def get_queue_item(tweet_id: int):
    """Get a single queue item."""
    rows = _db("SELECT * FROM tweet_queue WHERE id=?", (tweet_id,))
    if not rows:
        raise HTTPException(404, "Tweet not found")
    item = rows[0]
    if item.get("thread_tweets"):
        try:
            item["thread_tweets"] = json.loads(item["thread_tweets"])
        except (json.JSONDecodeError, TypeError):
            pass
    return item


@router.put("/queue/{tweet_id}/edit")
async def edit_tweet(tweet_id: int, req: EditTweetRequest):
    """Edit a pending tweet's content."""
    rows = _db("SELECT * FROM tweet_queue WHERE id=?", (tweet_id,))
    if not rows:
        raise HTTPException(404, "Tweet not found")
    if len(req.content) > 280:
        raise HTTPException(400, "Tweet exceeds 280 characters")
    _db("UPDATE tweet_queue SET content=? WHERE id=?", (req.content, tweet_id), fetch=False)
    return {"updated": True, "id": tweet_id}


@router.post("/queue/{tweet_id}/approve")
async def approve_tweet(
    tweet_id: int,
    background_tasks: BackgroundTasks,
    post_now: bool = False,
    account_id: int | None = None,
):
    """Approve a tweet. If post_now=true, posts immediately."""
    rows = _db("SELECT * FROM tweet_queue WHERE id=?", (tweet_id,))
    if not rows:
        raise HTTPException(404, "Tweet not found")

    if account_id:
        _db("UPDATE tweet_queue SET status='approved', account_id=? WHERE id=?", (account_id, tweet_id), fetch=False)
    else:
        _db("UPDATE tweet_queue SET status='approved' WHERE id=?", (tweet_id,), fetch=False)

    if post_now:
        background_tasks.add_task(_post_tweet, tweet_id, account_id or rows[0].get("account_id"))
        return {"approved": True, "posting": True, "message": "Approved and posting now..."}

    return {"approved": True, "posting": False, "message": "Approved. Ready to post."}


@router.post("/queue/{tweet_id}/reject")
async def reject_tweet(tweet_id: int):
    """Reject a tweet from the queue."""
    _db("UPDATE tweet_queue SET status='rejected' WHERE id=?", (tweet_id,), fetch=False)
    return {"rejected": True}


@router.post("/queue/{tweet_id}/restore")
async def restore_tweet(tweet_id: int):
    """Restore a rejected tweet back to pending."""
    _db("UPDATE tweet_queue SET status='pending' WHERE id=?", (tweet_id,), fetch=False)
    return {"restored": True}


@router.post("/queue/approve-all")
async def approve_all_pending(
    background_tasks: BackgroundTasks,
    post_now: bool = False,
    account_id: int | None = None,
):
    """Approve all pending tweets."""
    pending = _db("SELECT id, account_id FROM tweet_queue WHERE status='pending'")
    for row in pending:
        if account_id:
            _db("UPDATE tweet_queue SET status='approved', account_id=? WHERE id=?", (account_id, row["id"]), fetch=False)
        else:
            _db("UPDATE tweet_queue SET status='approved' WHERE id=?", (row["id"],), fetch=False)
        if post_now:
            background_tasks.add_task(_post_tweet, row["id"], account_id or row.get("account_id"))
    return {"approved": len(pending), "posting": post_now}


# ─── Posting ──────────────────────────────────────────────────────────────────

async def _post_tweet(tweet_id: int, account_id: int | None = None):
    """Post a tweet or thread using account credentials."""
    rows = _db("SELECT * FROM tweet_queue WHERE id=?", (tweet_id,))
    if not rows:
        return

    tweet = rows[0]
    acct_id = account_id or tweet.get("account_id")
    account = _get_account(acct_id)

    if not account:
        _db(
            "UPDATE tweet_queue SET status='error', error_message=? WHERE id=?",
            ("No X account connected. Add one in the Twitter Hub.", tweet_id),
            fetch=False,
        )
        return

    try:
        if tweet["tweet_type"] == "thread":
            thread_tweets = json.loads(tweet.get("thread_tweets") or "[]")
            if not thread_tweets:
                thread_tweets = [tweet["content"]]

            # Post first tweet
            result = await _post_to_x(thread_tweets[0], account)
            if not result["success"]:
                _db(
                    "UPDATE tweet_queue SET status='error', error_message=? WHERE id=?",
                    (result["error"], tweet_id), fetch=False,
                )
                return

            first_id = result["post_id"]
            last_id = first_id

            # Post reply chain
            for t in thread_tweets[1:]:
                import asyncio
                await asyncio.sleep(1)
                r = await _post_to_x(t, account, reply_to_id=last_id)
                if r["success"]:
                    last_id = r["post_id"]
                else:
                    break

            _db(
                """UPDATE tweet_queue
                   SET status='posted', posted_at=?, tweet_id=?, post_url=?
                   WHERE id=?""",
                (datetime.now().isoformat(), first_id, result.get("post_url"), tweet_id),
                fetch=False,
            )
        else:
            result = await _post_to_x(tweet["content"], account)
            if result["success"]:
                _db(
                    """UPDATE tweet_queue
                       SET status='posted', posted_at=?, tweet_id=?, post_url=?
                       WHERE id=?""",
                    (datetime.now().isoformat(), result["post_id"], result.get("post_url"), tweet_id),
                    fetch=False,
                )
            else:
                _db(
                    "UPDATE tweet_queue SET status='error', error_message=? WHERE id=?",
                    (result["error"], tweet_id), fetch=False,
                )
    except Exception as e:
        logger.error("Tweet posting failed: %s", e)
        _db(
            "UPDATE tweet_queue SET status='error', error_message=? WHERE id=?",
            (str(e), tweet_id), fetch=False,
        )


@router.post("/queue/{tweet_id}/post")
async def post_tweet_now(tweet_id: int, background_tasks: BackgroundTasks, account_id: int | None = None):
    """Post a specific tweet immediately."""
    rows = _db("SELECT * FROM tweet_queue WHERE id=?", (tweet_id,))
    if not rows:
        raise HTTPException(404, "Tweet not found")
    background_tasks.add_task(_post_tweet, tweet_id, account_id or rows[0].get("account_id"))
    return {"posting": True, "tweet_id": tweet_id}


# ─── Manual Tweet ─────────────────────────────────────────────────────────────

@router.post("/tweet/manual")
async def manual_tweet(req: ManualTweetRequest, background_tasks: BackgroundTasks):
    """Write and optionally post a manual tweet."""
    if len(req.content) > 280:
        raise HTTPException(400, "Tweet exceeds 280 characters")

    tweet_id = _db(
        """INSERT INTO tweet_queue (content, tweet_type, status, niche, hook_type, account_id)
           VALUES (?, 'single', 'approved', 'manual', 'manual', ?)""",
        (req.content, req.account_id),
        fetch=False,
    )

    if req.post_now:
        background_tasks.add_task(_post_tweet, tweet_id, req.account_id)
        return {"queued": True, "id": tweet_id, "posting": True}

    return {"queued": True, "id": tweet_id, "posting": False}


# ─── Posted History ───────────────────────────────────────────────────────────

@router.get("/posted")
async def get_posted_tweets(limit: int = 20):
    """Get history of posted tweets."""
    items = _db(
        "SELECT * FROM tweet_queue WHERE status='posted' ORDER BY posted_at DESC LIMIT ?",
        (limit,),
    )
    for item in items:
        if item.get("thread_tweets"):
            try:
                item["thread_tweets"] = json.loads(item["thread_tweets"])
            except (json.JSONDecodeError, TypeError):
                pass
    return {"posted": len(items), "items": items}


# ─── Trend-Aware Auto-Generate ────────────────────────────────────────────────


def _get_top_trends(niche: str, limit: int = 5) -> list[str]:
    """Fetch cached trend signals for a niche from the trend store."""
    try:
        from app.core.store.trend_store import get_signals

        signals = get_signals(niche)
        if signals:
            sorted_signals = sorted(signals, key=lambda s: s.get("momentum_score", 0), reverse=True)
            return [s.get("headline") or s.get("title", "") for s in sorted_signals[:limit] if s.get("headline") or s.get("title")]
    except Exception as e:
        logger.debug("[auto-gen] trend fetch failed: %s", e)
    return []


@router.post("/auto-generate")
async def auto_generate_daily(
    niche: str = "AI and marketing",
    target_audience: str = "entrepreneurs",
    count: int = 5,
    account_id: int | None = None,
    auto_approve: bool = False,
):
    """Generate a daily content batch incorporating live trends.

    If auto_approve=True, tweets go straight to 'approved' status
    (for autonomy level >= semi_auto).
    """
    trends = _get_top_trends(niche)
    trend_block = ""
    if trends:
        trend_list = "\n".join(f"  - {t}" for t in trends[:5])
        trend_block = f"""

Current trending topics in your niche (incorporate 2-3 of these):
{trend_list}
Write tweets that ride these trends with a unique angle or hot take."""

    pillars = ["education", "opinion", "behind_scenes", "engagement"]

    prompt = f"""You are a viral Twitter/X content creator. Generate {count} tweets for a {niche} account targeting {target_audience}.

Content mix: {', '.join(pillars)}
{trend_block}

Rules:
- Each tweet MUST be under 280 characters
- Use proven viral hooks: numbers, questions, contrarian takes, "hot take:", "unpopular opinion:"
- No hashtags in tweet body (max 1-2 at end if truly relevant)
- Conversational, human tone — not corporate
- Make people want to reply, retweet, or follow
- Also generate 1 thread (5 connected tweets)

Respond ONLY with valid JSON (no markdown, no explanation):
{{
    "tweets": [
        {{
            "content": "the tweet text (max 280 chars)",
            "hook_type": "question|stat|hot_take|story|tip|contrarian",
            "pillar": "education|opinion|engagement|behind_scenes",
            "ai_score": 85,
            "best_time": "9am|12pm|6pm|8pm"
        }}
    ],
    "thread": {{
        "hook": "First tweet that hooks readers",
        "tweets": ["1/ Hook...", "2/ ...", "3/ ...", "4/ ...", "5/ CTA..."],
        "topic": "thread topic",
        "ai_score": 90
    }}
}}"""

    response = await _ask_ollama(prompt)
    data = _extract_json(response)

    if not data:
        return {
            "error": "Generation failed — is Ollama running?",
            "hint": f"Run: ollama serve && ollama pull {OLLAMA_MODEL}",
            "auto_generated": False,
            "generated": 0,
            "items": [],
        }

    initial_status = "approved" if auto_approve else "pending"
    added = []

    for tweet in data.get("tweets", []):
        content = tweet.get("content", "").strip()
        if not content or len(content) > 280:
            continue
        tweet_id = _db(
            """INSERT INTO tweet_queue
               (content, tweet_type, niche, hook_type, pillar, ai_score, best_time, account_id, status)
               VALUES (?, 'single', ?, ?, ?, ?, ?, ?, ?)""",
            (
                content, niche, tweet.get("hook_type", ""), tweet.get("pillar", ""),
                tweet.get("ai_score", 70), tweet.get("best_time", ""), account_id, initial_status,
            ),
            fetch=False,
        )
        added.append({"id": tweet_id, "type": "single", "content": content, "status": initial_status})

    thread = data.get("thread")
    if thread:
        thread_tweets = thread.get("tweets", [])
        hook = thread.get("hook", thread_tweets[0] if thread_tweets else "")
        if hook:
            thread_id = _db(
                """INSERT INTO tweet_queue
                   (content, tweet_type, thread_tweets, niche, hook_type, pillar, ai_score, account_id, status)
                   VALUES (?, 'thread', ?, ?, 'thread', 'education', ?, ?, ?)""",
                (hook, json.dumps(thread_tweets), niche, thread.get("ai_score", 85), account_id, initial_status),
                fetch=False,
            )
            added.append({"id": thread_id, "type": "thread", "content": hook, "status": initial_status})

    return {
        "auto_generated": True,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "generated": len(added),
        "trends_used": trends[:5] if trends else [],
        "auto_approved": auto_approve,
        "items": added,
    }


async def run_daily_auto_generation() -> dict:
    """Called by the background scheduler. Generates content for all active accounts."""
    accounts = _db("SELECT * FROM twitter_accounts WHERE is_active=1")
    if not accounts:
        logger.info("[daily-gen] no active accounts, skipping")
        return {"skipped": True, "reason": "no active accounts"}

    results = {}
    for acct in accounts:
        niche = acct.get("niche") or "general"
        audience = acct.get("target_audience") or "general audience"
        account_id = acct["id"]

        # Check daily post limit — don't generate if already at limit
        today = datetime.now().strftime("%Y-%m-%d")
        today_count = _db(
            "SELECT COUNT(*) as c FROM tweet_queue WHERE account_id=? AND created_at >= ? AND status != 'rejected'",
            (account_id, today),
        )[0]["c"]
        if today_count >= 10:
            logger.info("[daily-gen] account=%s already has %d items today, skipping", acct["username"], today_count)
            results[acct["username"]] = {"skipped": True, "reason": f"already {today_count} items today"}
            continue

        try:
            result = await auto_generate_daily(
                niche=niche,
                target_audience=audience,
                count=5,
                account_id=account_id,
                auto_approve=False,  # Always draft for now; user approves
            )
            results[acct["username"]] = {
                "generated": result.get("generated", 0),
                "trends_used": result.get("trends_used", []),
            }
            logger.info(
                "[daily-gen] account=@%s generated=%d trends=%d",
                acct["username"], result.get("generated", 0), len(result.get("trends_used", [])),
            )
        except Exception as e:
            logger.error("[daily-gen] account=@%s failed: %s", acct["username"], e)
            results[acct["username"]] = {"error": str(e)}

    return results


async def run_auto_post_approved() -> dict:
    """Post all approved tweets that haven't been posted yet. Called by background scheduler."""
    approved = _db("SELECT * FROM tweet_queue WHERE status='approved' ORDER BY ai_score DESC LIMIT 17")
    if not approved:
        return {"posted": 0}

    posted = 0
    for item in approved:
        try:
            await _post_tweet(item["id"], item.get("account_id"))
            posted += 1
            # Respect rate limits — space posts 2 minutes apart
            import asyncio
            await asyncio.sleep(120)
        except Exception as e:
            logger.error("[auto-post] tweet %d failed: %s", item["id"], e)
            break

    return {"posted": posted}


# ─── Strategy Generator ──────────────────────────────────────────────────────

@router.post("/strategy")
async def generate_strategy(niche: str, target_audience: str, account_goal: str = "grow followers and build authority"):
    """Generate a complete Twitter growth strategy using AI."""
    prompt = f"""Create a complete Twitter/X growth strategy for a brand new account.

Niche: {niche}
Target Audience: {target_audience}
Goal: {account_goal}

This account starts at 0 followers. Build it organically without paid ads.

Respond ONLY with valid JSON (no markdown, no explanation):
{{
    "account_setup": {{
        "bio": "perfect 160-char bio",
        "pinned_tweet": "the perfect first pinned tweet",
        "profile_keywords": ["keyword1", "keyword2", "keyword3"]
    }},
    "content_pillars": [
        {{"pillar": "name", "percentage": 30, "description": "what to post", "example": "example tweet"}},
        {{"pillar": "name", "percentage": 25, "description": "...", "example": "..."}},
        {{"pillar": "name", "percentage": 25, "description": "...", "example": "..."}},
        {{"pillar": "name", "percentage": 20, "description": "...", "example": "..."}}
    ],
    "posting_schedule": {{
        "tweets_per_day": 3,
        "best_times": ["9:00 AM", "12:00 PM", "6:00 PM"],
        "thread_frequency": "1 per week",
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    }},
    "growth_tactics": [
        {{"tactic": "...", "time_per_day": "15 min", "expected_followers_month1": "50-100"}},
        {{"tactic": "...", "time_per_day": "10 min", "expected_followers_month1": "30-60"}}
    ],
    "hashtag_strategy": {{
        "use_hashtags": false,
        "reason": "2024+ Twitter algorithm prefers no hashtags",
        "exception": "Only 1-2 if trending and relevant"
    }},
    "month_1_milestones": ["milestone 1", "milestone 2", "milestone 3"],
    "month_3_projection": "X-Y followers",
    "month_6_projection": "X-Y followers",
    "viral_content_formula": "The formula that works for this niche"
}}"""

    response = await _ask_ollama(prompt)
    data = _extract_json(response)
    if not data:
        return {"error": "Strategy generation failed — is Ollama running?"}
    return data


# ─── Delete ───────────────────────────────────────────────────────────────────

@router.delete("/queue/{tweet_id}")
async def delete_queue_item(tweet_id: int):
    """Delete a tweet from the queue."""
    _db("DELETE FROM tweet_queue WHERE id=?", (tweet_id,), fetch=False)
    return {"deleted": True}
