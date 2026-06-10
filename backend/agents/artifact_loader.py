"""artifact_loader.py — cold-load retrieval + evidence artifacts from S3 or local repo.

If EE_RETRIEVAL_S3 is set (e.g. s3://ee-toolbox-retrieval-207258148366):
  1. Fetch s3://<bucket>/latest.json to discover the current version and
     sha256 hashes (published by .github/workflows/publish-retrieval-artifacts.yml).
  2. For each artifact, download to EE_ARTIFACT_CACHE
     (default ~/.cache/ee-toolbox/artifacts/<version>/) unless a cached copy
     already exists with a matching sha256.
  3. Decompress evidence_corpus.db.zst -> evidence_corpus.db in the cache dir.
  4. Return paths for: embeddings, corpus, profiles, manifest, evidence_db.

If EE_RETRIEVAL_S3 is unset: return the local repo/backend paths unchanged
(current behaviour — zero network traffic, zero behaviour change).

Transport: boto3 if importable (optional EE_AWS_PROFILE selects a profile),
otherwise an ``aws s3 cp`` subprocess (with ``--profile $EE_AWS_PROFILE`` if
set). Both paths are read-only S3 GETs — the bucket is only ever WRITTEN by
the GitHub Actions OIDC workflow, per the B1 brief's locked decision.

``init_from_env()`` is the one-shot startup hook: it is called from
``stub_tools.build_ee_mcp_server`` and, when (and only when) EE_RETRIEVAL_S3
is set, repoints the evidence drill-down store and the hybrid retrieval index
at the cached artifact paths.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ENV_S3 = "EE_RETRIEVAL_S3"
ENV_CACHE = "EE_ARTIFACT_CACHE"
ENV_PROFILE = "EE_AWS_PROFILE"
ENV_REPO_ROOT = "EE_REPO_ROOT"

# backend/agents/artifact_loader.py -> parents[2] == repo root
_REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[2]

_RETRIEVAL_FILES = {
    "embeddings": "embeddings.npy",
    "corpus": "corpus.json",
    "profiles": "profiles.json",
    "manifest": "manifest.json",
}
_EVIDENCE_ZST = "evidence_corpus.db.zst"
_EVIDENCE_DB = "evidence_corpus.db"


def _repo_root() -> Path:
    env = os.environ.get(ENV_REPO_ROOT, "").strip()
    return Path(env) if env else _REPO_ROOT_DEFAULT


def _cache_root() -> Path:
    env = os.environ.get(ENV_CACHE, "").strip()
    if env:
        return Path(env)
    return Path.home() / ".cache" / "ee-toolbox" / "artifacts"


def _local_paths() -> dict[str, Path]:
    root = _repo_root()
    artifacts = root / "pipeline" / "retrieval" / "artifacts"
    return {
        "embeddings": artifacts / "embeddings.npy",
        "corpus": artifacts / "corpus.json",
        "profiles": artifacts / "profiles.json",
        "manifest": artifacts / "manifest.json",
        "evidence_db": root / "backend" / "data" / "evidence_corpus.db",
    }


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_s3_url(url: str) -> tuple[str, str]:
    """Split s3://bucket[/prefix] into (bucket, prefix-with-trailing-slash-or-empty)."""
    if not url.startswith("s3://"):
        raise ValueError(f"{ENV_S3} must be an s3:// URL, got {url!r}")
    rest = url[len("s3://"):].strip("/")
    if not rest:
        raise ValueError(f"{ENV_S3} has no bucket: {url!r}")
    bucket, _, prefix = rest.partition("/")
    return bucket, (prefix + "/") if prefix else ""


def _fetch_s3(bucket: str, key: str, dest: Path) -> None:
    """Download one S3 object to ``dest``. Monkeypatch point for tests.

    boto3 preferred; falls back to the aws CLI. EE_AWS_PROFILE selects a
    credentials profile on either path (useful for local read-only runs with
    the ai-prod profile).
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    profile = os.environ.get(ENV_PROFILE, "").strip() or None
    try:
        import boto3  # type: ignore

        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        client = session.client("s3")
        logger.info("artifact_loader: downloading s3://%s/%s -> %s", bucket, key, dest)
        client.download_file(bucket, key, str(dest))
        return
    except ImportError:
        pass
    cmd = ["aws", "s3", "cp", f"s3://{bucket}/{key}", str(dest)]
    if profile:
        cmd += ["--profile", profile]
    logger.info("artifact_loader: %s", " ".join(cmd))
    subprocess.run(cmd, check=True, capture_output=True)


def _ensure_file(
    bucket: str, key: str, dest: Path, expected_sha: str | None
) -> bool:
    """Ensure ``dest`` exists with the expected sha256.

    Returns True if a download happened, False on cache hit. Raises
    ValueError on checksum mismatch after download.
    """
    if dest.exists() and expected_sha and _sha256(dest) == expected_sha:
        logger.info("artifact_loader: cache hit for %s (sha256 ok)", dest.name)
        return False
    _fetch_s3(bucket, key, dest)
    if expected_sha:
        actual = _sha256(dest)
        if actual != expected_sha:
            raise ValueError(
                f"checksum mismatch for {dest.name}: "
                f"expected {expected_sha}, got {actual}"
            )
        logger.info("artifact_loader: downloaded %s (sha256 ok)", dest.name)
    return True


def _decompress_zst(src: Path, dest: Path) -> None:
    import zstandard

    logger.info("artifact_loader: decompressing %s -> %s", src.name, dest.name)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    dctx = zstandard.ZstdDecompressor()
    with src.open("rb") as f_in, tmp.open("wb") as f_out:
        dctx.copy_stream(f_in, f_out)
    tmp.replace(dest)  # atomic publish — no half-written DB visible

    # Settle WAL sidecars — freshly decompressed WAL-mode DB fails mode=ro until
    # a rw open initializes the -shm and -wal files.
    import sqlite3 as _sqlite3
    with _sqlite3.connect(str(dest)) as _conn:
        _conn.execute("PRAGMA integrity_check(1)")


def ensure_artifacts() -> dict[str, Path]:
    """Resolve (and if needed, cold-load) all retrieval + evidence artifacts.

    Returns {"embeddings", "corpus", "profiles", "manifest", "evidence_db"}
    -> Path. Local mode (EE_RETRIEVAL_S3 unset) returns repo paths unchanged
    and performs no network access.
    """
    s3_url = os.environ.get(ENV_S3, "").strip()
    if not s3_url:
        return _local_paths()

    bucket, prefix = _parse_s3_url(s3_url)
    cache_root = _cache_root()
    cache_root.mkdir(parents=True, exist_ok=True)

    # 1. latest.json is the discovery document — always fetched fresh.
    latest_path = cache_root / "latest.json"
    _fetch_s3(bucket, f"{prefix}latest.json", latest_path)
    latest: dict[str, Any] = json.loads(latest_path.read_text(encoding="utf-8"))
    retrieval_ver = str(latest["retrieval"])
    evidence_ver = str(latest["evidence"])
    sha256s: dict[str, str] = latest.get("sha256", {})

    paths: dict[str, Path] = {}

    # 2. The four retrieval index artifacts.
    retrieval_dir = cache_root / retrieval_ver
    for name, filename in _RETRIEVAL_FILES.items():
        dest = retrieval_dir / filename
        _ensure_file(
            bucket,
            f"{prefix}retrieval/{retrieval_ver}/{filename}",
            dest,
            sha256s.get(filename),
        )
        paths[name] = dest

    # 3. Compressed evidence corpus + decompression.
    evidence_dir = cache_root / evidence_ver
    zst_path = evidence_dir / _EVIDENCE_ZST
    db_path = evidence_dir / _EVIDENCE_DB
    downloaded = _ensure_file(
        bucket,
        f"{prefix}evidence/{evidence_ver}/{_EVIDENCE_ZST}",
        zst_path,
        sha256s.get(_EVIDENCE_ZST),
    )
    if downloaded or not db_path.exists():
        _decompress_zst(zst_path, db_path)
    paths["evidence_db"] = db_path

    return paths


# ---------------------------------------------------------------------------
# One-shot startup wiring (flag-guarded by EE_RETRIEVAL_S3)
# ---------------------------------------------------------------------------

_init_lock = threading.Lock()
_initialized = False


def init_from_env() -> None:
    """Resolve artifacts once per process and repoint the consumers.

    No-op unless EE_RETRIEVAL_S3 is set: in local mode the existing default
    paths in evidence_tools / hybrid_search already match _local_paths(), so
    nothing needs touching.
    """
    global _initialized
    if _initialized or not os.environ.get(ENV_S3, "").strip():
        return
    with _init_lock:
        if _initialized:
            return
        paths = ensure_artifacts()

        from agents.evidence_tools import set_evidence_db

        set_evidence_db(paths["evidence_db"])

        import sys

        repo_root = str(_repo_root())
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from pipeline.retrieval.hybrid_search import get_index

        get_index(
            corpus_path=str(paths["corpus"]),
            embeddings_path=str(paths["embeddings"]),
            profiles_path=str(paths["profiles"]),
            manifest_path=str(paths["manifest"]),
        )
        _initialized = True
        logger.info(
            "artifact_loader: S3 cold-load complete (evidence_db=%s)",
            paths["evidence_db"],
        )
