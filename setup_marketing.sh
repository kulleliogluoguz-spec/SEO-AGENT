#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  AI Growth OS — Marketing Engine Entegrasyon Script'i
#  
#  KULLANIM:
#    1. Bu script'i SEO-AGENT repo klasörünüzün içine kopyalayın
#    2. chmod +x setup_marketing.sh
#    3. ./setup_marketing.sh
# ═══════════════════════════════════════════════════════════════

set -e

echo "═══════════════════════════════════════════════════════"
echo " AI Growth OS — Marketing Execution Engine Kurulumu"
echo "═══════════════════════════════════════════════════════"
echo ""

# Repo root'ta olduğumuzu kontrol et
if [ ! -f "docker-compose.yml" ] || [ ! -d "apps/api/app" ]; then
    echo "❌ HATA: Bu script'i SEO-AGENT repo'nuzun root klasöründe çalıştırın!"
    echo "   Beklenen yapı: ./apps/api/app/ mevcut olmalı"
    exit 1
fi

echo "✓ Repo yapısı doğrulandı"
echo ""

# ── 1. Marketing Backend Klasörlerini Oluştur ─────────────────
echo "📁 Backend klasörleri oluşturuluyor..."

mkdir -p apps/api/app/agents/marketing
mkdir -p apps/api/app/api/endpoints/marketing
mkdir -p apps/api/app/connectors/social
mkdir -p apps/api/app/models
mkdir -p apps/api/app/schemas/marketing
mkdir -p apps/api/app/services/marketing
mkdir -p apps/api/app/workers/marketing
mkdir -p apps/api/app/prompts/marketing

echo "✓ Backend klasörleri oluşturuldu"

# ── 2. __init__.py Dosyalarını Oluştur ─────────────────────────
echo "📄 __init__.py dosyaları oluşturuluyor..."

touch apps/api/app/agents/marketing/__init__.py
touch apps/api/app/api/endpoints/marketing/__init__.py
touch apps/api/app/connectors/social/__init__.py
touch apps/api/app/schemas/marketing/__init__.py
touch apps/api/app/services/marketing/__init__.py
touch apps/api/app/workers/marketing/__init__.py
touch apps/api/app/prompts/marketing/__init__.py

echo "✓ __init__.py dosyaları oluşturuldu"

# ── 3. Frontend Klasörlerini Oluştur ───────────────────────────
echo "📁 Frontend klasörleri oluşturuluyor..."

mkdir -p apps/web/src/types
mkdir -p apps/web/src/lib/api

echo "✓ Frontend klasörleri oluşturuldu"

echo ""
echo "═══════════════════════════════════════════════════════"
echo " Klasör yapısı hazır!"
echo ""
echo " Şimdi marketing-engine-files/ klasöründeki dosyaları"
echo " aşağıdaki hedeflere kopyalayın:"
echo ""
echo " KAYNAK → HEDEF:"
echo " ─────────────────────────────────────────────────────"
echo " agents.py         → apps/api/app/agents/marketing/agents.py"
echo " base.py           → apps/api/app/connectors/social/base.py"
echo " channels.py       → apps/api/app/connectors/social/channels.py"
echo " social__init__.py → apps/api/app/connectors/social/__init__.py"
echo " marketing_models.py → apps/api/app/models/marketing.py"
echo " schemas.py        → apps/api/app/schemas/marketing/schemas.py"
echo " compliance.py     → apps/api/app/services/marketing/compliance.py"
echo " service.py        → apps/api/app/services/marketing/service.py"
echo " routes.py         → apps/api/app/api/endpoints/marketing/routes.py"
echo " workflows.py      → apps/api/app/workers/marketing/workflows.py"
echo " prompts.py        → apps/api/app/prompts/marketing/prompts.py"
echo " mktg_migration.py → apps/api/alembic/versions/mktg_001_marketing_tables.py"
echo " marketing.ts      → apps/web/src/types/marketing.ts"
echo " marketing_api.ts  → apps/web/src/lib/api/marketing.ts"
echo ""
echo " Son adım: main.py'ye router'ı ekleyin (aşağıya bakın)"
echo "═══════════════════════════════════════════════════════"
