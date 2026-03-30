"""
Integration tests for core API endpoints.
Uses SQLite in-memory via conftest fixtures — no external DB required.
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Workspace, Recommendation, RecommendationStatus


class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_liveness_returns_ok(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_readiness_returns_ready(self, client: AsyncClient):
        r = await client.get("/health/ready")
        assert r.status_code in (200, 503)  # 503 if DB not reachable
        assert r.json()["status"] in ("ready", "not_ready")

    @pytest.mark.asyncio
    async def test_root_returns_name(self, client: AsyncClient):
        r = await client.get("/")
        assert r.status_code == 200
        assert "AI CMO OS" in r.json()["name"]


class TestAuthRegisterLogin:
    @pytest.mark.asyncio
    async def test_register_creates_user(self, client: AsyncClient):
        r = await client.post("/api/v1/auth/register", json={
            "email": "newuser@test.com",
            "password": "NewUser1234!",
            "full_name": "New User",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["email"] == "newuser@test.com"
        assert "hashed_password" not in data
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email_returns_409(self, client: AsyncClient):
        payload = {"email": "dup@test.com", "password": "Password1!", "full_name": "Dup"}
        await client.post("/api/v1/auth/register", json=payload)
        r = await client.post("/api/v1/auth/register", json=payload)
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_register_weak_password_returns_422(self, client: AsyncClient):
        r = await client.post("/api/v1/auth/register", json={
            "email": "weak@test.com", "password": "short", "full_name": "Weak",
        })
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_login_returns_tokens(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "email": "logintest@test.com", "password": "LoginTest1!", "full_name": "Login",
        })
        r = await client.post("/api/v1/auth/login", json={
            "email": "logintest@test.com", "password": "LoginTest1!",
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "email": "badpass@test.com", "password": "Correct1234!", "full_name": "Bad",
        })
        r = await client.post("/api/v1/auth/login", json={
            "email": "badpass@test.com", "password": "WrongPassword1!",
        })
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unknown_email_returns_401(self, client: AsyncClient):
        r = await client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com", "password": "Password1!",
        })
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_me_returns_user_when_authenticated(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert r.status_code == 200
        assert "email" in r.json()
        assert "hashed_password" not in r.json()

    @pytest.mark.asyncio
    async def test_me_returns_403_without_token(self, client: AsyncClient):
        r = await client.get("/api/v1/auth/me")
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_me_returns_401_with_garbage_token(self, client: AsyncClient):
        r = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})
        assert r.status_code == 401


class TestSiteEndpoints:
    @pytest.mark.asyncio
    async def test_onboard_site_in_unknown_workspace_returns_404(
        self, client: AsyncClient, auth_headers
    ):
        fake_id = str(uuid.uuid4())
        r = await client.post(
            f"/api/v1/sites?workspace_id={fake_id}",
            json={"url": "https://valid-site.com", "max_pages": 10},
            headers=auth_headers,
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_onboard_invalid_url_returns_422(
        self, client: AsyncClient, auth_headers, demo_user, db_session: AsyncSession
    ):
        from sqlalchemy import select
        ws = (await db_session.execute(select(Workspace).where(Workspace.slug == "test-workspace"))).scalar_one()
        r = await client.post(
            f"/api/v1/sites?workspace_id={ws.id}",
            json={"url": "not-a-url"},
            headers=auth_headers,
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_onboard_valid_site_creates_record(
        self, client: AsyncClient, auth_headers, demo_user, db_session: AsyncSession
    ):
        from sqlalchemy import select
        ws = (await db_session.execute(select(Workspace).where(Workspace.slug == "test-workspace"))).scalar_one()
        r = await client.post(
            f"/api/v1/sites?workspace_id={ws.id}",
            json={"url": "https://new-site-test.com", "max_pages": 5},
            headers=auth_headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["domain"] == "new-site-test.com"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_duplicate_site_returns_409(
        self, client: AsyncClient, auth_headers, demo_user, db_session: AsyncSession
    ):
        from sqlalchemy import select
        ws = (await db_session.execute(select(Workspace).where(Workspace.slug == "test-workspace"))).scalar_one()
        payload = {"url": "https://dup-check.com", "max_pages": 5}
        await client.post(f"/api/v1/sites?workspace_id={ws.id}", json=payload, headers=auth_headers)
        r = await client.post(f"/api/v1/sites?workspace_id={ws.id}", json=payload, headers=auth_headers)
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_get_nonexistent_site_returns_404(self, client: AsyncClient, auth_headers):
        r = await client.get(f"/api/v1/sites/{uuid.uuid4()}", headers=auth_headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_list_sites_returns_paginated(
        self, client: AsyncClient, auth_headers, demo_site
    ):
        r = await client.get(
            f"/api/v1/sites?workspace_id={demo_site.workspace_id}",
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1


class TestRecommendationEndpoints:
    @pytest.mark.asyncio
    async def test_list_recommendations_empty_by_default(
        self, client: AsyncClient, auth_headers, demo_site
    ):
        r = await client.get(
            f"/api/v1/recommendations?site_id={demo_site.id}",
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_recommendations_returns_seeded_data(
        self, client: AsyncClient, auth_headers, demo_site, db_session: AsyncSession
    ):
        # Seed a recommendation
        rec = Recommendation(
            id=uuid.uuid4(),
            site_id=demo_site.id,
            workspace_id=demo_site.workspace_id,
            title="Fix missing title",
            category="technical_seo",
            summary="Page missing title tag",
            rationale="Titles improve CTR significantly",
            impact_score=0.8, effort_score=0.1,
            confidence_score=0.95, urgency_score=0.9,
            priority_score=0.88,
            status=RecommendationStatus.PENDING,
        )
        db_session.add(rec)
        await db_session.commit()

        r = await client.get(
            f"/api/v1/recommendations?site_id={demo_site.id}",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["total"] == 1
        item = r.json()["items"][0]
        assert item["title"] == "Fix missing title"
        assert item["priority_score"] == 0.88

    @pytest.mark.asyncio
    async def test_get_nonexistent_recommendation_returns_404(
        self, client: AsyncClient, auth_headers
    ):
        r = await client.get(f"/api/v1/recommendations/{uuid.uuid4()}", headers=auth_headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_update_recommendation_status(
        self, client: AsyncClient, auth_headers, demo_site, db_session: AsyncSession
    ):
        rec = Recommendation(
            id=uuid.uuid4(),
            site_id=demo_site.id, workspace_id=demo_site.workspace_id,
            title="Test rec", category="technical_seo",
            summary="Summary", rationale="Rationale",
            impact_score=0.5, effort_score=0.5, confidence_score=0.5,
            urgency_score=0.5, priority_score=0.5,
            status=RecommendationStatus.PENDING,
        )
        db_session.add(rec)
        await db_session.commit()

        r = await client.patch(
            f"/api/v1/recommendations/{rec.id}",
            json={"status": "approved"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "approved"


class TestApprovalEndpoints:
    @pytest.mark.asyncio
    async def test_list_approvals_returns_empty(
        self, client: AsyncClient, auth_headers, demo_site
    ):
        from app.models.models import Workspace
        from sqlalchemy import select
        r = await client.get(
            f"/api/v1/approvals?workspace_id={demo_site.workspace_id}",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["items"] == []


class TestContentEndpoints:
    @pytest.mark.asyncio
    async def test_list_content_returns_empty(
        self, client: AsyncClient, auth_headers, demo_site
    ):
        r = await client.get(
            f"/api/v1/content?workspace_id={demo_site.workspace_id}",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["items"] == []
