# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Morphsec88

import hashlib
import re
import struct
from typing import FrozenSet

DEFAULT_STOPWORDS: FrozenSet[str] = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
    "to", "was", "were", "will", "with", "this", "but", "or", "not",
})


def popcount(value: int) -> int:
    """Return the Hamming weight (number of set bits) of an integer."""
    if hasattr(int, "bit_count"):
        return value.bit_count()
    return bin(value).count("1")


class BitEncoder:
    """Deterministic N-gram bitvector encoder using BLAKE2b hashing."""

    def __init__(
        self,
        width: int = 4096,
        ngram_size: int = 3,
        hashes_per_ngram: int = 2,
        strip_stopwords: bool = True,
    ):
        if width <= 0 or (width & (width - 1)) != 0:
            raise ValueError("Vector width must be a power of two (e.g., 1024, 2048, 4096).")
        self.width = width
        self.mask = width - 1
        self.ngram_size = ngram_size
        self.hashes_per_ngram = hashes_per_ngram
        self.strip_stopwords = strip_stopwords

    def encode(self, text: str) -> int:
        """Project normalized input text into a fixed-width D-bit integer mask."""
        cleaned = re.sub(r"[^\w\s]", "", text.lower())
        tokens = cleaned.split()
        if self.strip_stopwords and len(tokens) > 2:
            filtered = [t for t in tokens if t not in DEFAULT_STOPWORDS]
            if filtered:
                tokens = filtered

        normalized = f" {' '.join(tokens)} "
        if len(normalized) < self.ngram_size:
            return 0

        vector = 0
        limit = len(normalized) - self.ngram_size + 1

        for i in range(limit):
            chunk = normalized[i : i + self.ngram_size].encode("utf-8")
            digest = hashlib.blake2b(chunk, digest_size=16).digest()
            positions = struct.unpack("<4I", digest)

            for h in range(self.hashes_per_ngram):
                bit_pos = positions[h % 4] & self.mask
                vector |= 1 << bit_pos

        return vector
