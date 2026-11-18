# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Morphsec88

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
from .encoder import popcount
from .module import ComputeModule


class DecisionType(Enum):
    SHORT_CIRCUIT = "short_circuit"
    CONSTRUCTIVE_INTERFERENCE = "constructive_interference"
    CONFIDENCE_GATE = "confidence_gate"
    EMPTY_SIGNAL = "empty_signal"


@dataclass(frozen=True)
class FilterDecision:
    decision: DecisionType
    selected_modules: List[ComputeModule]
    consensus_vector: int
    top_sharpness: float
    top_z_score: float
    noise_floor: float
    consensus_confidence: float
    effective_vote_threshold: int


class HallwayFilter:
    """Bitwise DSP arbitrator with contender-sparsity gating and Z-score normalization."""

    def __init__(
        self,
        vector_width: int = 4096,
        z_short_circuit: float = 3.2,
        z_consensus_member: float = 1.5,
        min_z_margin: float = 1.0,
        min_raw_sharpness: float = 0.35,
        max_contenders_ratio: float = 0.08,
        min_contenders_cap: int = 4,
        max_mask_density: float = 0.30,
        min_consensus_votes: Optional[int] = None,
        confidence_threshold: float = 0.40,
        max_wake_modules: int = 3,
    ):
        self.vector_width = vector_width
        self.z_short_circuit = z_short_circuit
        self.z_consensus_member = z_consensus_member
        self.min_z_margin = min_z_margin
        self.min_raw_sharpness = min_raw_sharpness
        self.max_contenders_ratio = max_contenders_ratio
        self.min_contenders_cap = min_contenders_cap
        self.max_mask_density = max_mask_density
        self.min_consensus_votes = min_consensus_votes
        self.confidence_threshold = confidence_threshold
        self.max_wake_modules = max_wake_modules

    def _dynamic_vote_threshold(self, num_modules: int, avg_noise: float) -> int:
        if self.min_consensus_votes is not None:
            return self.min_consensus_votes
        expected_random_hits = num_modules * avg_noise * 1.45
        return max(2, int(round(expected_random_hits + 1.5)))

    def arbitrate(
        self,
        query_vector: int,
        shadows: List[Tuple[ComputeModule, int]],
    ) -> FilterDecision:
        query_energy = popcount(query_vector)
        if query_energy == 0 or not shadows:
            return FilterDecision(
                decision=DecisionType.EMPTY_SIGNAL,
                selected_modules=[],
                consensus_vector=0,
                top_sharpness=0.0,
                top_z_score=0.0,
                noise_floor=0.0,
                consensus_confidence=0.0,
                effective_vote_threshold=0,
            )

        n = len(shadows)

        # Hallway Contender Gating: skip zero shadows for fast bit-sliced counting
        max_contenders = max(self.min_contenders_cap, int(n * self.max_contenders_ratio))
        non_zero_shadows = [item for item in shadows if item[1] > 0]
        if len(non_zero_shadows) > max_contenders:
            crowded_bits = self._bits_at_least_k(non_zero_shadows, max_contenders + 1)
            exclusive_mask = ~crowded_bits
        else:
            exclusive_mask = ~0

        energies: List[float] = []
        raw_hits: List[int] = []
        exclusive_shadows: List[int] = []

        for mod, shadow in shadows:
            if shadow == 0:
                exclusive_shadows.append(0)
                raw_hits.append(0)
                energies.append(0.0)
                continue
            excl_shadow = shadow & exclusive_mask
            exclusive_shadows.append(excl_shadow)
            raw_energy = popcount(excl_shadow)
            raw_hits.append(raw_energy)
            mask_density = popcount(mod.knowledge_mask) / self.vector_width
            specificity = max(0.05, 1.0 - mask_density)
            energies.append((raw_energy / query_energy) * specificity)

        # Population mean (mu) and standard deviation (sigma) across all rooms
        mu = sum(energies) / n
        if n > 1:
            variance = sum((e - mu) ** 2 for e in energies) / n
            sigma = math.sqrt(variance)
        else:
            sigma = 0.0

        scored = []
        for idx, (mod, _) in enumerate(shadows):
            e_i = energies[idx]
            z_i = (e_i - mu) / sigma if sigma > 1e-9 else 0.0
            scored.append((z_i, e_i, raw_hits[idx], exclusive_shadows[idx], mod))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)

        top_z, _, top_raw, top_shadow, top_module = scored[0]
        second_z = scored[1][0] if len(scored) > 1 else 0.0
        z_margin = top_z - second_z
        top_sharpness = top_raw / query_energy
        top_density = popcount(top_module.knowledge_mask) / self.vector_width

        if n > 1:
            noise_sum = sum(item[2] for item in scored[1:])
            noise_floor = (noise_sum / (n - 1)) / query_energy
        else:
            noise_floor = 0.0

        # Step 1: Unique Z-score outlier check (Zero-Compute Short-Circuit)
        if (
            top_z >= self.z_short_circuit
            and z_margin >= self.min_z_margin
            and top_sharpness >= self.min_raw_sharpness
            and top_density <= self.max_mask_density
        ):
            return FilterDecision(
                decision=DecisionType.SHORT_CIRCUIT,
                selected_modules=[top_module],
                consensus_vector=top_shadow,
                top_sharpness=top_sharpness,
                top_z_score=top_z,
                noise_floor=noise_floor,
                consensus_confidence=top_sharpness,
                effective_vote_threshold=1,
            )

        # Step 2: Constructive interference among realistic contenders
        filtered_pairs = [(mod, excl_sh) for _, _, _, excl_sh, mod in scored if excl_sh > 0]
        vote_threshold = self._dynamic_vote_threshold(max(2, len(filtered_pairs)), noise_floor)
        consensus_vector = self._bits_at_least_k(filtered_pairs, vote_threshold)
        consensus_energy = popcount(consensus_vector)
        consensus_confidence = consensus_energy / query_energy

        if consensus_confidence >= self.confidence_threshold and top_z >= self.z_consensus_member:
            contributors = [
                mod
                for z_i, _, raw, shadow, mod in scored
                if z_i >= self.z_consensus_member
                and popcount(shadow & consensus_vector) >= max(1, int(query_energy * 0.25))
            ]
            if not contributors:
                contributors = [
                    mod for _, _, raw, _, mod in scored[: self.max_wake_modules] if raw > 0
                ]

            return FilterDecision(
                decision=DecisionType.CONSTRUCTIVE_INTERFERENCE,
                selected_modules=contributors[: self.max_wake_modules],
                consensus_vector=consensus_vector,
                top_sharpness=top_sharpness,
                top_z_score=top_z,
                noise_floor=noise_floor,
                consensus_confidence=consensus_confidence,
                effective_vote_threshold=vote_threshold,
            )

        # Step 3: Confidence Gate (Selective wake-up of top candidate rooms)
        candidates = [
            mod for _, _, raw, _, mod in scored[: self.max_wake_modules] if raw > 0
        ]
        if not candidates:
            candidates = [mod for _, _, _, _, mod in scored[: self.max_wake_modules]]

        for mod in candidates:
            mod.wake_deep_compute()

        return FilterDecision(
            decision=DecisionType.CONFIDENCE_GATE,
            selected_modules=candidates,
            consensus_vector=consensus_vector,
            top_sharpness=top_sharpness,
            top_z_score=top_z,
            noise_floor=noise_floor,
            consensus_confidence=consensus_confidence,
            effective_vote_threshold=vote_threshold,
        )

    def _bits_at_least_k(
        self, shadows: List[Tuple[ComputeModule, int]], threshold: int
    ) -> int:
        """Bit-sliced vertical carry-save adder returning bits active in >= threshold shadows."""
        if not shadows:
            return 0
        if threshold <= 1:
            result = 0
            for _, shadow in shadows:
                result |= shadow
            return result

        bit_planes: List[int] = []
        for _, shadow in shadows:
            carry = shadow
            for idx in range(len(bit_planes)):
                next_carry = bit_planes[idx] & carry
                bit_planes[idx] ^= carry
                carry = next_carry
                if carry == 0:
                    break
            if carry:
                bit_planes.append(carry)

        gt = 0
        eq = ~0
        max_bits = max(len(bit_planes), threshold.bit_length())

        for bit_idx in range(max_bits - 1, -1, -1):
            plane = bit_planes[bit_idx] if bit_idx < len(bit_planes) else 0
            t_bit = (threshold >> bit_idx) & 1

            if t_bit == 1:
                eq &= plane
            else:
                gt |= eq & plane
                eq &= ~plane

        return gt | eq
