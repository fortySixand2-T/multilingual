"""Single-port SPA serving (app/main._mount_spa).

When a built SPA is present, the app serves it on the API's origin. The catch-all
must not swallow API 404s: a path under a real API prefix that matched no route
returns JSON (not the SPA shell), while genuine client-side routes fall back to
index.html. Regression guard for QA issue 416.

Uses a throwaway `web_dist` so it runs in CI, where the real `web/dist` is absent.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def _fake_dist(tmp_path: Path) -> Path:
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("// built bundle\n")
    (tmp_path / "index.html").write_text("<!doctype html><title>TEF</title>")
    return tmp_path


def test_unmatched_api_path_returns_json_404(tmp_path):
    client = TestClient(create_app(web_dist=_fake_dist(tmp_path)))
    # `/exam/blueprints/{id}` was never registered — a real API 404, not a route.
    res = client.get("/exam/blueprints/does-not-exist")
    assert res.status_code == 404
    assert res.headers["content-type"].startswith("application/json")
    assert res.json() == {"detail": "Not Found"}


def test_client_side_route_falls_back_to_index_html(tmp_path):
    client = TestClient(create_app(web_dist=_fake_dist(tmp_path)))
    for path in ("/", "/path", "/lessons/greetings-01"):
        res = client.get(path)
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/html")
        assert "<title>TEF</title>" in res.text


def test_registered_api_route_still_served(tmp_path):
    client = TestClient(create_app(web_dist=_fake_dist(tmp_path)))
    res = client.get("/health")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/json")


def test_index_html_is_no_cache(tmp_path):
    # The shell must revalidate every load so a deploy's new asset hashes are picked
    # up instead of a cached index pinning stale JS.
    client = TestClient(create_app(web_dist=_fake_dist(tmp_path)))
    for path in ("/", "/lessons/greetings-01"):
        res = client.get(path)
        assert res.headers.get("cache-control") == "no-cache"


def test_hashed_assets_are_immutable(tmp_path):
    # Content-hashed bundles can be cached forever (their name changes each build).
    client = TestClient(create_app(web_dist=_fake_dist(tmp_path)))
    res = client.get("/assets/app.js")
    assert res.status_code == 200
    assert res.headers.get("cache-control") == "public, max-age=31536000, immutable"
