"""
AI Learning & Memory — learns from user feedback to improve recommendations.
PostgreSQL for structured preferences + Chroma (optional) for semantic search.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
CHROMA_DIR = "/Users/oguzkullelioglu/Desktop/ai-cmo-os 2/storage/chroma"


def _row_to_dict(row) -> dict:
    if row is None:
        return {}
    return dict(row._mapping)


class AIMemoryService:
    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        self._chroma = None
        self._embedder = None

    def _get_chroma(self):
        if self._chroma is None:
            try:
                import chromadb  # type: ignore

                self._chroma = chromadb.PersistentClient(path=CHROMA_DIR)
            except Exception as e:
                logger.warning("Chroma not available: %s", e)
                self._chroma = False
        return self._chroma

    def _get_embedder(self):
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore

                self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception as e:
                logger.warning("sentence-transformers not available: %s", e)
                self._embedder = False
        return self._embedder

    async def record_feedback(
        self,
        db: AsyncSession,
        module: str,
        recommendation: dict,
        action: str,
        modification: dict | None = None,
    ) -> None:
        await db.execute(
            text(
                """
                INSERT INTO ai_feedback(
                    workspace_id, module, feedback_type,
                    original_recommendation, user_action
                )
                VALUES(:wid, :mod, :ft, CAST(:orig AS jsonb), CAST(:act AS jsonb))
                """
            ),
            {
                "wid": self.workspace_id,
                "mod": module,
                "ft": action,
                "orig": json.dumps(recommendation),
                "act": json.dumps(modification or {"action": action}),
            },
        )
        await self._update_preference(db, module, recommendation, action)
        await db.commit()

    async def _update_preference(
        self, db: AsyncSession, module: str, recommendation: dict, action: str
    ) -> None:
        key = f"pref_{recommendation.get('type', 'unknown')}"
        r = await db.execute(
            text(
                "SELECT value, observation_count FROM ai_memory "
                "WHERE workspace_id=:wid AND module=:mod AND key=:key"
            ),
            {"wid": self.workspace_id, "mod": module, "key": key},
        )
        row = r.fetchone()
        if row:
            row = _row_to_dict(row)
            pref = row["value"] if isinstance(row["value"], dict) else {}
            cnt = (row["observation_count"] or 0) + 1
            accepts = pref.get("accepts", 0) + (1 if action == "accepted" else 0)
            rejects = pref.get("rejects", 0) + (1 if action == "rejected" else 0)
            rate = accepts / (accepts + rejects) if (accepts + rejects) > 0 else 0.5
            await db.execute(
                text(
                    """
                    UPDATE ai_memory
                       SET value = CAST(:v AS jsonb),
                           observation_count = :cnt,
                           confidence = :conf,
                           last_updated = NOW()
                     WHERE workspace_id=:wid AND module=:mod AND key=:key
                    """
                ),
                {
                    "v": json.dumps({"accepts": accepts, "rejects": rejects, "accept_rate": rate}),
                    "cnt": cnt,
                    "conf": min(0.95, 0.5 + rate * 0.5),
                    "wid": self.workspace_id,
                    "mod": module,
                    "key": key,
                },
            )
        else:
            await db.execute(
                text(
                    """
                    INSERT INTO ai_memory(
                        workspace_id, module, memory_type, key, value, confidence
                    )
                    VALUES(:wid, :mod, 'preference', :key, CAST(:v AS jsonb), 0.5)
                    ON CONFLICT(workspace_id, module, key) DO NOTHING
                    """
                ),
                {
                    "wid": self.workspace_id,
                    "mod": module,
                    "key": key,
                    "v": json.dumps(
                        {
                            "accepts": 1 if action == "accepted" else 0,
                            "rejects": 1 if action == "rejected" else 0,
                        }
                    ),
                },
            )

    async def get_preferences(self, db: AsyncSession, module: str) -> dict:
        r = await db.execute(
            text(
                "SELECT key, value, confidence, observation_count FROM ai_memory "
                "WHERE workspace_id=:wid AND module=:mod"
            ),
            {"wid": self.workspace_id, "mod": module},
        )
        prefs: dict = {}
        for row in r.fetchall():
            d = _row_to_dict(row)
            prefs[d["key"]] = {
                "value": d["value"],
                "confidence": float(d["confidence"] or 0),
                "observations": d["observation_count"],
            }
        return prefs

    async def store_call_embedding(self, call_id: str, transcript: str, analysis: dict) -> None:
        chroma = self._get_chroma()
        embedder = self._get_embedder()
        if not chroma or not embedder:
            return
        try:
            emb = embedder.encode([transcript[:2000]])[0].tolist()
            col = chroma.get_or_create_collection(
                f"calls_{self.workspace_id[:20]}",
                metadata={"hnsw:space": "cosine"},
            )
            col.add(
                ids=[call_id],
                embeddings=[emb],
                metadatas=[
                    {
                        "call_id": call_id,
                        "score": analysis.get("qualification_score", 0),
                        "category": analysis.get("qualification_category", "?"),
                    }
                ],
                documents=[transcript[:2000]],
            )
        except Exception as e:
            logger.error("Embedding store failed: %s", e)

    async def find_similar_calls(self, query: str, n: int = 5) -> list:
        chroma = self._get_chroma()
        embedder = self._get_embedder()
        if not chroma or not embedder:
            return []
        try:
            emb = embedder.encode([query])[0].tolist()
            col = chroma.get_collection(f"calls_{self.workspace_id[:20]}")
            results = col.query(query_embeddings=[emb], n_results=n)
            return results.get("metadatas", [[]])[0]
        except Exception:
            return []

    async def get_summary(self, db: AsyncSession) -> dict:
        r = await db.execute(
            text(
                "SELECT module, feedback_type, COUNT(*) AS cnt FROM ai_feedback "
                "WHERE workspace_id=:wid GROUP BY module, feedback_type"
            ),
            {"wid": self.workspace_id},
        )
        feedback = [_row_to_dict(row) for row in r.fetchall()]
        mc = await db.execute(
            text("SELECT COUNT(*) AS cnt FROM ai_memory WHERE workspace_id=:wid"),
            {"wid": self.workspace_id},
        )
        mem_count = int(_row_to_dict(mc.fetchone()).get("cnt") or 0)
        return {
            "total_feedback": sum(int(r.get("cnt") or 0) for r in feedback),
            "feedback_by_module": feedback,
            "learned_preferences": mem_count,
            "status": "active" if mem_count > 0 else "gathering_data",
        }
