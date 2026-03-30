"""
═══════════════════════════════════════════════════════════════
MAIN.PY ENTEGRASYONU

Sizin mevcut apps/api/app/main.py dosyanızda şu değişiklikleri yapın:
═══════════════════════════════════════════════════════════════

ADIM 1: Dosyanın üst kısmına (diğer import'ların yanına) ekleyin:
"""

# ↓↓↓ Bu satırı import bölümüne ekleyin ↓↓↓
from app.api.endpoints.marketing.routes import router as marketing_router

"""
ADIM 2: Router kayıtlarının olduğu yere (diğer app.include_router satırlarının yanına) ekleyin:
"""

# ↓↓↓ Bu satırı diğer include_router satırlarının yanına ekleyin ↓↓↓
app.include_router(marketing_router, prefix="/api/v1")
# veya prefix olmadan doğrudan:
# app.include_router(marketing_router)

"""
═══════════════════════════════════════════════════════════════
ÖRNEK — Mevcut main.py'niz muhtemelen şuna benzer:
═══════════════════════════════════════════════════════════════
"""

# ------- MEVCUT main.py ŞABLONU (referans) -------

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Mevcut import'larınız
from app.api.endpoints import auth, sites, crawls, recommendations, content, approvals, reports, connectors
from app.core.config import settings

# ▼▼▼ YENİ: Marketing router import'u ▼▼▼
from app.api.endpoints.marketing.routes import router as marketing_router

app = FastAPI(
    title="AI CMO OS",
    version="2.0.0",
    description="AI Growth Operating System + Marketing Execution Engine",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mevcut router'larınız
# app.include_router(auth.router)
# app.include_router(sites.router)
# app.include_router(crawls.router)
# ... vs

# ▼▼▼ YENİ: Marketing router'ı ekleyin ▼▼▼
app.include_router(marketing_router)

# Health check
@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "marketing_engine": True}
