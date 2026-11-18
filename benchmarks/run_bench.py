# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Morphsec88

import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from arbitrator.encoder import BitEncoder
from arbitrator.engine import ArbitratorEngine
from arbitrator.module import ComputeModule


def build_engine(num_modules: int, width: int = 1024) -> ArbitratorEngine:
    random.seed(88)
    encoder = BitEncoder(width=width)
    engine = ArbitratorEngine(encoder=encoder)

    m0 = ComputeModule(0, "routine_greeting", encoder)
    m0.ingest_patterns(["hello", "hi", "good morning", "hey"])
    engine.register_module(m0)

    m1 = ComputeModule(1, "systems_arch", encoder)
    m1.ingest_patterns(["processor", "register", "bitwise", "memory"])
    engine.register_module(m1)

    m2 = ComputeModule(2, "cryptography", encoder)
    m2.ingest_patterns(["encryption", "hash", "algorithm", "key"])
    engine.register_module(m2)

    vocab = ["data", "packet", "protocol", "network", "interface", "buffer", "instruction", "cycle"]
    for i in range(3, num_modules):
        mod = ComputeModule(i, f"domain_{i}", encoder)
        samples = [f"{random.choice(vocab)} {random.choice(vocab)} {i}" for _ in range(3)]
        mod.ingest_patterns(samples)
        engine.register_module(mod)

    return engine


def run_benchmark(num_modules: int, iterations: int = 500) -> None:
    engine = build_engine(num_modules=num_modules)
    queries = [
        "Hello!",
        "processor encryption bitwise",
        "completely unknown ambiguous input query string",
    ]

    print(f"--- BENCHMARK: {num_modules} modules | 1024-bit vector | {iterations} iterations ---")
    for q in queries:
        latencies = []
        last_report = None
        for _ in range(iterations):
            last_report = engine.process(q)
            latencies.append(last_report.latency_us)

        avg_us = statistics.mean(latencies)
        p99_us = sorted(latencies)[int(iterations * 0.99)]
        print(
            f"Query: '{q[:32]:<32}' | Decision: {last_report.decision.decision.value:<25} "
            f"| Avg: {avg_us:7.2f} us | P99: {p99_us:7.2f} us | Woken: {last_report.woken_modules}"
        )
    print()


if __name__ == "__main__":
    run_benchmark(num_modules=100)
    run_benchmark(num_modules=1000)
