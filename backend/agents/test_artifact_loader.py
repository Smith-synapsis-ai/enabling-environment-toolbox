"""Zero-network unit tests for agents.artifact_loader (B1-W3).

All S3 access goes through artifact_loader._fetch_s3, which these tests
monkeypatch — no test here ever opens a socket.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from agents import artifact_loader
from agents.artifact_loader import ensure_artifacts


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_latest(cache: Path, sha256s: dict[str, str]) -> dict:
    doc = {"retrieval": "v1", "evidence": "v1", "sha256": sha256s}
    (cache / "latest.json").write_text(json.dumps(doc), encoding="utf-8")
    return doc


@pytest.fixture
def no_network(monkeypatch):
    """Hard-fail if anything tries to reach S3."""
    def _boom(bucket, key, dest):  # pragma: no cover - should never run
        raise AssertionError(f"unexpected network fetch: s3://{bucket}/{key}")

    monkeypatch.setattr(artifact_loader, "_fetch_s3", _boom)


def test_local_mode_passthrough(monkeypatch, no_network):
    """EE_RETRIEVAL_S3 unset -> repo paths returned, zero network calls."""
    monkeypatch.delenv(artifact_loader.ENV_S3, raising=False)
    paths = ensure_artifacts()
    root = artifact_loader._repo_root()
    assert paths["embeddings"] == root / "pipeline/retrieval/artifacts/embeddings.npy"
    assert paths["corpus"] == root / "pipeline/retrieval/artifacts/corpus.json"
    assert paths["profiles"] == root / "pipeline/retrieval/artifacts/profiles.json"
    assert paths["manifest"] == root / "pipeline/retrieval/artifacts/manifest.json"
    assert paths["evidence_db"] == root / "backend/data/evidence_corpus.db"


def test_checksum_mismatch_raises(monkeypatch, tmp_path):
    """Downloaded file whose sha256 != latest.json -> ValueError with both hashes."""
    cache = tmp_path / "cache"
    cache.mkdir()
    monkeypatch.setenv(artifact_loader.ENV_S3, "s3://test-bucket")
    monkeypatch.setenv(artifact_loader.ENV_CACHE, str(cache))

    good = b"expected artifact bytes"
    bad = b"corrupted download bytes"
    expected_sha = _sha256_bytes(good)
    actual_sha = _sha256_bytes(bad)
    latest = _write_latest(cache, {"embeddings.npy": expected_sha})

    def fake_fetch(bucket, key, dest: Path):
        dest.parent.mkdir(parents=True, exist_ok=True)
        if key.endswith("latest.json"):
            dest.write_text(json.dumps(latest), encoding="utf-8")
        else:
            dest.write_bytes(bad)  # every artifact arrives corrupted

    monkeypatch.setattr(artifact_loader, "_fetch_s3", fake_fetch)

    with pytest.raises(ValueError) as exc_info:
        ensure_artifacts()
    msg = str(exc_info.value)
    assert "embeddings.npy" in msg
    assert expected_sha in msg
    assert actual_sha in msg


def test_cache_hit_skips_download(monkeypatch, tmp_path):
    """Cached artifacts with matching sha256 -> no artifact fetches at all."""
    cache = tmp_path / "cache"
    cache.mkdir()
    monkeypatch.setenv(artifact_loader.ENV_S3, "s3://test-bucket")
    monkeypatch.setenv(artifact_loader.ENV_CACHE, str(cache))

    # Pre-populate the cache: four retrieval artifacts + decompressed DB
    # + the .zst, all matching latest.json hashes.
    import zstandard

    sha256s: dict[str, str] = {}
    ver_dir = cache / "v1"
    ver_dir.mkdir()
    for filename in ["embeddings.npy", "corpus.json", "profiles.json", "manifest.json"]:
        data = f"cached:{filename}".encode()
        (ver_dir / filename).write_bytes(data)
        sha256s[filename] = _sha256_bytes(data)

    db_bytes = b"sqlite-ish evidence db contents"
    zst_bytes = zstandard.ZstdCompressor().compress(db_bytes)
    (ver_dir / "evidence_corpus.db.zst").write_bytes(zst_bytes)
    (ver_dir / "evidence_corpus.db").write_bytes(db_bytes)
    sha256s["evidence_corpus.db.zst"] = _sha256_bytes(zst_bytes)

    latest = _write_latest(cache, sha256s)

    fetch_calls: list[str] = []

    def fake_fetch(bucket, key, dest: Path):
        fetch_calls.append(key)
        if key.endswith("latest.json"):  # discovery doc is always fetched fresh
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(latest), encoding="utf-8")
            return
        raise AssertionError(f"artifact fetch should have been a cache hit: {key}")

    monkeypatch.setattr(artifact_loader, "_fetch_s3", fake_fetch)

    paths = ensure_artifacts()
    assert fetch_calls == ["latest.json"]  # only the discovery document
    assert paths["embeddings"] == ver_dir / "embeddings.npy"
    assert paths["evidence_db"] == ver_dir / "evidence_corpus.db"
    assert paths["evidence_db"].read_bytes() == db_bytes


def test_wal_settle_after_decompress(tmp_path, monkeypatch):
    """After _decompress_zst, the DB must be openable in read-only URI mode."""
    import sqlite3
    import zstandard

    # Create a minimal WAL-mode SQLite DB
    src_db = tmp_path / "test.db"
    con = sqlite3.connect(str(src_db))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    con.execute("INSERT INTO t VALUES (1)")
    con.commit()
    con.close()

    # Compress it
    src_zst = tmp_path / "test.db.zst"
    cctx = zstandard.ZstdCompressor(level=1)
    with src_db.open("rb") as f_in, src_zst.open("wb") as f_out:
        cctx.copy_stream(f_in, f_out)

    # Remove the original so only the .zst exists
    src_db.unlink()

    # Remove any WAL sidecars if they exist
    for sidecar in [tmp_path / "test.db-wal", tmp_path / "test.db-shm"]:
        if sidecar.exists():
            sidecar.unlink()

    # Decompress (this calls _decompress_zst which should apply WAL settle fix)
    from agents.artifact_loader import _decompress_zst
    dest = tmp_path / "output.db"
    _decompress_zst(src_zst, dest)

    # Must be openable in read-only mode without error
    con2 = sqlite3.connect(f"file:{dest}?mode=ro", uri=True)
    count = con2.execute("SELECT COUNT(*) FROM t").fetchone()[0]
    assert count == 1
    con2.close()
