"""Deterministic pseudo-embeddings for the no-Azure (FAKE / LOCAL) path.

Seed a NumPy RNG from a stable hash of the text and emit a normalized
EMBED_DIM vector. Same text -> same vector, every run, no Azure required.

Both FakeLLMClient.embed and scripts/embed_metadata.py (LOCAL path) call this,
so the vectors written to meta.* match the vectors a FAKE request would embed.
"""
from __future__ import annotations

import hashlib

import numpy as np

from .base import EMBED_DIM


def _seed_from_text(text: str) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    # First 8 bytes -> a stable 64-bit seed (independent of Python hash salting).
    return int.from_bytes(digest[:8], "big")


def pseudo_embed(text: str, dim: int = EMBED_DIM) -> list[float]:
    rng = np.random.default_rng(_seed_from_text(text))
    vec = rng.standard_normal(dim)
    norm = np.linalg.norm(vec)
    if norm == 0:
        norm = 1.0
    return (vec / norm).astype(float).tolist()
