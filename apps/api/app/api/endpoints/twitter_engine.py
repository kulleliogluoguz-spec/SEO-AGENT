"""
Twitter Autonomous Growth Engine

Generates AI content daily using Ollama, manages a tweet queue,
posts approved tweets via the existing XPublisher service,
and tracks performance metrics.

Leverages the existing XPublisher (httpx + OAuth 1.0a) — no tweepy needed.
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

# ─── SQLite Queue DB ──────────────────────────────────────────────────────────

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
    conn.commit()
    conn.close()


_init_db()


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
                # Strip <think>...</think> blocks from qwen3 reasoning
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


class ManualTweetRequest(BaseModel):
    content: str
    post_now: bool = False


class EditTweetRequest(BaseModel):
    content: str


# ─── Health & Stats ───────────────────────────────────────────────────────────

@router.get("/health")
async def twitter_health():
    """Check Twitter/X connection status using existing XPublisher."""
    from app.core.store.credential_store import get_credential
    from app.services.publishers.x_publisher import XPublisher

    # Try demo user first, then check env vars
    demo_user_id = "demo-user-id"
    cred = get_credential(demo_user_id, "x") or get_credential(demo_user_id, "twitter")

    if not cred:
        api_key = os.getenv("X_API_KEY") or os.getenv("TWITTER_API_KEY")
        access_token = os.getenv("X_ACCESS_TOKEN") or os.getenv("TWITTER_ACCESS_TOKEN")
        if not api_key:
            return {
                "status": "not_configured",
                "message": "No X/Twitter credentials found",
                "instructions": [
                    "1. Go to developer.twitter.com",
                    "2. Open your app > Keys and Tokens",
                    "3. Generate Access Token & Secret",
                    "4. Add to apps/api/.env:",
                    "   X_ACCESS_TOKEN=your_access_token",
                    "   X_ACCESS_TOKEN_SECRET=your_access_token_secret",
                    "5. Or connect via Dashboard > Connections > Connect X Account",
                ],
            }
        if not access_token:
            return {
                "status": "partial",
                "message": "API keys found but Access Token missing",
                "instructions": [
                    "Go to developer.twitter.com > Your App > Keys and Tokens",
                    "Generate Access Token & Secret (with Read+Write permissions)",
                    "Add X_ACCESS_TOKEN and X_ACCESS_TOKEN_SECRET to .env",
                ],
            }

    publisher = XPublisher(user_id=demo_user_id)
    pub_status = await publisher.check_status()

    if pub_status.value == "ready":
        return {
            "status": "connected",
            "message": "X account connected and ready to post",
            "publisher_status": pub_status.value,
        }

    return {
        "status": pub_status.value,
        "message": f"X connection issue: {pub_status.value}",
        "publisher_status": pub_status.value,
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
               (content, tweet_type, niche, hook_type, pillar, ai_score, best_time, status)
               VALUES (?, 'single', ?, ?, ?, ?, ?, 'pending')""",
            (
                content,
                req.niche,
                tweet.get("hook_type", ""),
                tweet.get("pillar", ""),
                tweet.get("ai_score", 70),
                tweet.get("best_time", ""),
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
               (content, tweet_type, thread_tweets, niche, hook_type, pillar, ai_score, status)
               VALUES (?, 'thread', ?, ?, 'thread', 'education', ?, 'pending')""",
            (hook, json.dumps(thread_tweets), req.niche, thread.get("ai_score", 85)),
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
async def approve_tweet(tweet_id: int, background_tasks: BackgroundTasks, post_now: bool = False):
    """Approve a tweet. If post_now=true, posts immediately to Twitter."""
    rows = _db("SELECT * FROM tweet_queue WHERE id=?", (tweet_id,))
    if not rows:
        raise HTTPException(404, "Tweet not found")

    _db("UPDATE tweet_queue SET status='approved' WHERE id=?", (tweet_id,), fetch=False)

    if post_now:
        background_tasks.add_task(_post_tweet, tweet_id)
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
async def approve_all_pending(background_tasks: BackgroundTasks, post_now: bool = False):
    """Approve all pending tweets."""
    pending = _db("SELECT id FROM tweet_queue WHERE status='pending'")
    for row in pending:
        _db("UPDATE tweet_queue SET status='approved' WHERE id=?", (row["id"],), fetch=False)
        if post_now:
            background_tasks.add_task(_post_tweet, row["id"])
    return {"approved": len(pending), "posting": post_now}


# ─── Posting ──────────────────────────────────────────────────────────────────

async def _post_tweet(tweet_id: int):
    """Post a tweet or thread using the existing XPublisher."""
    from app.services.publishers.x_publisher import XPublisher

    rows = _db("SELECT * FROM tweet_queue WHERE id=?", (tweet_id,))
    if not rows:
        return

    tweet = rows[0]
    publisher = XPublisher(user_id="demo-user-id")

    try:
        if tweet["tweet_type"] == "thread":
            thread_tweets = json.loads(tweet.get("thread_tweets") or "[]")
            if not thread_tweets:
                thread_tweets = [tweet["content"]]
            results = await publisher.publish_thread(thread_tweets)
            if results and results[0].success:
                _db(
                    """UPDATE tweet_queue
                       SET status='posted', posted_at=?, tweet_id=?, post_url=?
                       WHERE id=?""",
                    (datetime.now().isoformat(), results[0].post_id, results[0].post_url, tweet_id),
                    fetch=False,
                )
            else:
                error = results[0].error if results else "Unknown error"
                _db(
                    "UPDATE tweet_queue SET status='error', error_message=? WHERE id=?",
                    (str(error), tweet_id),
                    fetch=False,
                )
        else:
            result = await publisher.publish_text_post(tweet["content"])
            if result.success:
                _db(
                    """UPDATE tweet_queue
                       SET status='posted', posted_at=?, tweet_id=?, post_url=?
                       WHERE id=?""",
                    (datetime.now().isoformat(), result.post_id, result.post_url, tweet_id),
                    fetch=False,
                )
            else:
                _db(
                    "UPDATE tweet_queue SET status='error', error_message=? WHERE id=?",
                    (str(result.error), tweet_id),
                    fetch=False,
                )
    except Exception as e:
        logger.error("Tweet posting failed: %s", e)
        _db(
            "UPDATE tweet_queue SET status='error', error_message=? WHERE id=?",
            (str(e), tweet_id),
            fetch=False,
        )


@router.post("/queue/{tweet_id}/post")
async def post_tweet_now(tweet_id: int, background_tasks: BackgroundTasks):
    """Post a specific tweet immediately."""
    rows = _db("SELECT * FROM tweet_queue WHERE id=?", (tweet_id,))
    if not rows:
        raise HTTPException(404, "Tweet not found")
    background_tasks.add_task(_post_tweet, tweet_id)
    return {"posting": True, "tweet_id": tweet_id}


# ─── Manual Tweet ─────────────────────────────────────────────────────────────

@router.post("/tweet/manual")
async def manual_tweet(req: ManualTweetRequest, background_tasks: BackgroundTasks):
    """Write and optionally post a manual tweet."""
    if len(req.content) > 280:
        raise HTTPException(400, "Tweet exceeds 280 characters")

    tweet_id = _db(
        """INSERT INTO tweet_queue (content, tweet_type, status, niche, hook_type)
           VALUES (?, 'single', 'approved', 'manual', 'manual')""",
        (req.content,),
        fetch=False,
    )

    if req.post_now:
        background_tasks.add_task(_post_tweet, tweet_id)
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


# ─── Auto-Generate ────────────────────────────────────────────────────────────

@router.post("/auto-generate")
async def auto_generate_daily(niche: str = "AI and marketing", target_audience: str = "entrepreneurs", count: int = 5):
    """Generate daily content batch. Call via scheduler or cron."""
    req = GenerateRequest(
        niche=niche,
        target_audience=target_audience,
        count=count,
        include_threads=True,
    )
    result = await generate_tweets(req)
    return {
        "auto_generated": True,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "result": result,
    }


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
