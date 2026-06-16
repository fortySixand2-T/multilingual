"""AC0.9 — invite-code signup + JWT login + protected route.

Sets a temp DB and invite codes in the environment *before* importing the app,
so `app.db.session` binds its engine to the throwaway database.
"""
import asyncio
import os
import tempfile

_TMP_DB = os.path.join(tempfile.mkdtemp(), "auth_test.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP_DB}"
os.environ["INVITE_CODES"] = "good-code,second-code"
os.environ["JWT_SECRET"] = "test-secret"

from fastapi.testclient import TestClient  # noqa: E402

from app.config.settings import get_settings  # noqa: E402

get_settings.cache_clear()

from app.db.session import engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.users.models import Base  # noqa: E402


def _create_schema():
    async def go():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(go())


_create_schema()
client = TestClient(create_app())


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
