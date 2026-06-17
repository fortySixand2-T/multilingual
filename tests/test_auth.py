"""AC0.9 — invite-code signup + JWT login + protected route.

Fully isolated: its own engine + overridden get_session/get_settings, so it never
touches the global engine or a persistent DB (and is order-independent in the suite).
The real signup/login/JWT flow (get_current_user) is exercised unchanged.
"""

import asyncio
import tempfile

from fastapi.testclient import TestClient

from app.config.settings import Settings, get_settings
from app.db.session import get_session
from app.main import create_app
from app.users.models import Base

_DB = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/auth.db"

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

_engine = create_async_engine(_DB)
_Session = async_sessionmaker(_engine, expire_on_commit=False)
_settings = Settings(
    invite_codes="good-code,second-code",
    jwt_secret="test-secret-key-32-bytes-minimum!!",
    database_url=_DB,
)


def _create_schema():
    async def go():
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(go())


async def _override_session():
    async with _Session() as s:
        yield s


_create_schema()
app = create_app()
app.dependency_overrides[get_session] = _override_session
app.dependency_overrides[get_settings] = lambda: _settings
client = TestClient(app)


def test_signup_rejects_short_password():
    r = client.post(
        "/auth/signup",
        json={"email": "short@x.com", "password": "1", "invite_code": "good-code"},
    )
    assert r.status_code == 422  # min 8 chars (qa issue 002)


def test_signup_requires_valid_invite_code():
    r = client.post(
        "/auth/signup",
        json={"email": "a@x.com", "password": "pw123456", "invite_code": "nope"},
    )
    assert r.status_code == 403


def test_signup_login_and_protected_route():
    r = client.post(
        "/auth/signup",
        json={
            "email": "b@x.com",
            "password": "pw123456",
            "invite_code": "good-code",
            "display_name": "Bee",
        },
    )
    assert r.status_code == 201
    token = r.json()["access_token"]

    # protected route rejects missing token
    assert client.get("/auth/me").status_code == 401
    # ...and an invalid one
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401

    # valid token works
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "b@x.com"
    assert me.json()["display_name"] == "Bee"

    # login returns a working token too
    r2 = client.post("/auth/login", json={"email": "b@x.com", "password": "pw123456"})
    assert r2.status_code == 200
    token2 = r2.json()["access_token"]
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token2}"}).status_code == 200


def test_login_rejects_bad_password():
    client.post(
        "/auth/signup",
        json={"email": "c@x.com", "password": "rightpw12", "invite_code": "good-code"},
    )
    r = client.post("/auth/login", json={"email": "c@x.com", "password": "wrongpw12"})
    assert r.status_code == 401


def test_duplicate_email_conflicts():
    body = {"email": "dup@x.com", "password": "pw123456", "invite_code": "good-code"}
    assert client.post("/auth/signup", json=body).status_code == 201
    assert client.post("/auth/signup", json=body).status_code == 409
