# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Morphsec88

from collections import Counter
from typing import Iterable, Optional
from .encoder import BitEncoder, popcount


class ComputeModule:
    """Dormant domain-specific compute module with a sparsity-bounded knowledge bitmask."""

    def __init__(
        self,
        module_id: int,
        domain: str,
        encoder: BitEncoder,
        phase_seed: Optional[int] = None,
        max_density: float = 0.20,
    ):
        self.module_id = module_id
        self.domain = domain
        self.encoder = encoder
        self.knowledge_mask: int = 0
        self.phase_vector: int = phase_seed if phase_seed is not None else 0
        self.max_density: float = max_density
        self.woken_count: int = 0
        self._bit_counts: Counter[int] = Counter()

    def ingest_patterns(self, samples: Iterable[str]) -> None:
        """Accumulate training patterns with frequency-based pruning to prevent OR saturation."""
        for text in samples:
            vec = self.encoder.encode(text)
            while vec:
                lsb = vec & -vec
                bit_idx = lsb.bit_length() - 1
                self._bit_counts[bit_idx] += 1
                vec ^= lsb

        max_bits = max(1, int(self.encoder.width * self.max_density))
        if len(self._bit_counts) <= max_bits:
            mask = 0
            for bit_idx in self._bit_counts:
                mask |= 1 << bit_idx
            self.knowledge_mask = mask
        else:
            top_bits = self._bit_counts.most_common(max_bits)
            mask = 0
            for bit_idx, _ in top_bits:
                mask |= 1 << bit_idx
            self.knowledge_mask = mask

    @property
    def mask_density(self) -> float:
        """Return the fraction of active bits in the knowledge mask."""
        return popcount(self.knowledge_mask) / self.encoder.width

    def project_shadow(self, broadcast_signal: int) -> int:
        """Compute lightweight shadow response via single-cycle bitwise intersection."""
        aligned_signal = broadcast_signal ^ self.phase_vector if self.phase_vector else broadcast_signal
        return aligned_signal & self.knowledge_mask

    def wake_deep_compute(self) -> None:
        """Simulate waking the module for full-precision deep computation."""
        self.woken_count += 1
