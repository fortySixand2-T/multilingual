"""AC0.8 (local-FS) — object storage round-trip + config-driven factory."""
from app.storage.factory import build_storage
from app.storage.interface import ObjectStorage
from app.storage.local_fs import LocalFileStorage


class _Settings:
    storage_backend = "local"

    def __init__(self, d):
        self.local_storage_dir = d


def test_factory_builds_local_backend(tmp_path):
    store = build_storage(_Settings(str(tmp_path / "assets")))
    assert isinstance(store, LocalFileStorage)
    assert isinstance(store, ObjectStorage)  # satisfies the protocol


def test_unknown_backend_raises(tmp_path):
    s = _Settings(str(tmp_path))
    s.storage_backend = "ftp"
    try:
        build_storage(s)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_local_fs_put_get_delete_url(tmp_path):
    store = LocalFileStorage(str(tmp_path / "assets"))
    url = store.put("audio/a1/bonjour.mp3", b"\x00\x01data", content_type="audio/mpeg")
    assert url.startswith("file://")
    assert store.get("audio/a1/bonjour.mp3") == b"\x00\x01data"

    store.delete("audio/a1/bonjour.mp3")
    store.delete("audio/a1/bonjour.mp3")  # idempotent: deleting again is a no-op


def test_local_fs_nested_keys_create_dirs(tmp_path):
    store = LocalFileStorage(str(tmp_path / "assets"))
    store.put("deep/nested/key.txt", b"hi")
    assert store.get("deep/nested/key.txt") == b"hi"
