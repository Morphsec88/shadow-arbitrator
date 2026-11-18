# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Morphsec88

import time
from dataclasses import dataclass
from typing import List, Optional
from .encoder import BitEncoder
from .filter import FilterDecision, HallwayFilter
from .module import ComputeModule


@dataclass(frozen=True)
class ExecutionReport:
    query: str
    decision: FilterDecision
    latency_us: float
    total_modules: int
    woken_modules: int


class ArbitratorEngine:
    """Core execution engine coordinating zero-hop broadcast and shadow arbitration."""

    def __init__(
        self,
        encoder: Optional[BitEncoder] = None,
        hallway_filter: Optional[HallwayFilter] = None,
    ):
        self.encoder = encoder or BitEncoder(width=4096)
        self.filter = hallway_filter or HallwayFilter(vector_width=self.encoder.width)
        self.modules: List[ComputeModule] = []

    def register_module(self, module: ComputeModule) -> None:
        self.modules.append(module)

    def process(self, query: str) -> ExecutionReport:
        t0 = time.perf_counter()

        # Phase 1: Zero-Hop Broadcast
        signal = self.encoder.encode(query)

        # Phase 2: Parallel Shadow Projection
        shadows = [(mod, mod.project_shadow(signal)) for mod in self.modules]

        # Phase 3: Hallway DSP Arbitration
        woken_before = sum(m.woken_count for m in self.modules)
        decision = self.filter.arbitrate(signal, shadows)
        woken_after = sum(m.woken_count for m in self.modules)

        latency_us = (time.perf_counter() - t0) * 1_000_000

        return ExecutionReport(
            query=query,
            decision=decision,
            latency_us=latency_us,
            total_modules=len(self.modules),
            woken_modules=woken_after - woken_before,
        )
