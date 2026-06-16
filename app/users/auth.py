from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time

import jwt  # PyJWT

ALGO = "HS256"

# Password hashing via stdlib PBKDF2 — no extra dependency at this scale.
_PBKDF2_ALGO = "pbkdf2_sha256"
_PBKDF2_ITERATIONS = 200_000


def create_token(*, subject: str, secret: str, ttl_seconds: int = 7 * 24 * 3600) -> str:
    now = int(time.time())
    return jwt.encode({"sub": subject, "iat": now, "exp": now + ttl_seconds}, secret, algorithm=ALGO)


def verify_token(token: str, secret: str) -> dict:
    return jwt.decode(token, secret, algorithms=[ALGO])


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def hash_password(password: str, *, iterations: int = _PBKDF2_ITERATIONS) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{_PBKDF2_ALGO}${iterations}${_b64(salt)}${_b64(dk)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters_s, salt_b64, hash_b64 = stored.split("$")
        if algo != _PBKDF2_ALGO:
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), base64.b64decode(salt_b64), int(iters_s)
        )
        return hmac.compare_digest(dk, base64.b64decode(hash_b64))
    except (ValueError, TypeError):
        return False
