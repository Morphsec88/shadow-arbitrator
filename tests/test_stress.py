# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Morphsec88

import random
import statistics
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from arbitrator.encoder import BitEncoder
from arbitrator.engine import ArbitratorEngine
from arbitrator.filter import DecisionType, HallwayFilter
from arbitrator.module import ComputeModule


class TestStressArbitrator(unittest.TestCase):
    """10,000-query stress test measuring False Positive, False Negative, and latency."""

    def test_10k_queries_stress(self):
        random.seed(88)
        width = 4096
        encoder = BitEncoder(width=width)
        hallway_filter = HallwayFilter(vector_width=width)
        engine = ArbitratorEngine(encoder=encoder, hallway_filter=hallway_filter)

        domains = {
            "auth_security": ["oauth token", "jwt signature", "password hash", "ssh certificate"],
            "kernel_memory": ["page fault", "virtual memory", "spinlock mutex", "syscall interrupt"],
            "network_stack": ["tcp handshake", "udp socket", "packet routing", "dns resolver"],
            "storage_engine": ["btree index", "write ahead log", "disk sector", "checksum block"],
            "crypto_core": ["elliptic curve", "aes cipher", "merkle tree", "zero knowledge proof"],
        }

        for idx, (name, patterns) in enumerate(domains.items()):
            mod = ComputeModule(idx, name, encoder)
            mod.ingest_patterns(patterns)
            engine.register_module(mod)

        # Register 194 background rooms + 1 heavily overfed room (saturation test)
        bg_vocab = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "theta", "omega", "node", "cluster"]
        for idx in range(5, 199):
            mod = ComputeModule(idx, f"bg_domain_{idx}", encoder)
            mod.ingest_patterns([f"{random.choice(bg_vocab)} {random.choice(bg_vocab)} {idx}" for _ in range(4)])
            engine.register_module(mod)

        overfed = ComputeModule(199, "saturated_room", encoder, max_density=0.20)
        overfed.ingest_patterns([f"common filler text sample {i} {random.choice(bg_vocab)}" for i in range(300)])
        engine.register_module(overfed)

        # Build 10,000 queries: 4,000 known (clean + noisy), 6,000 unknown/out-of-domain
        known_queries = []
        domain_items = list(domains.items())
        for _ in range(4000):
            target_domain, patterns = random.choice(domain_items)
            base = random.choice(patterns)
            if random.random() < 0.35:
                # Inject mild typo / noise
                pos = random.randint(1, max(1, len(base) - 2))
                noisy = base[:pos] + random.choice("xyzq") + base[pos + 1 :]
                known_queries.append((noisy, target_domain))
            else:
                known_queries.append((base, target_domain))

        unknown_words = [
            "sourdough", "cucumber", "gardening", "violin", "astronomy", "telescope",
            "espresso", "mountain", "bicycle", "umbrella", "symphony", "watercolor",
            "volcano", "penguin", "strawberry", "architecture", "origami", "marathon",
        ]
        unknown_queries = [
            " ".join(random.sample(unknown_words, k=random.randint(2, 5)))
            for _ in range(6000)
        ]

        false_negatives = 0
        false_positives = 0
        latencies = []

        for query, expected_domain in known_queries:
            report = engine.process(query)
            latencies.append(report.latency_us)
            matched_domains = [m.domain for m in report.decision.selected_modules]
            if report.decision.decision == DecisionType.CONFIDENCE_GATE or expected_domain not in matched_domains:
                false_negatives += 1

        for query in unknown_queries:
            report = engine.process(query)
            latencies.append(report.latency_us)
            if report.decision.decision in (DecisionType.SHORT_CIRCUIT, DecisionType.CONSTRUCTIVE_INTERFERENCE):
                false_positives += 1

        fn_rate = (false_negatives / len(known_queries)) * 100.0
        fp_rate = (false_positives / len(unknown_queries)) * 100.0
        avg_us = statistics.mean(latencies)
        p99_us = sorted(latencies)[int(len(latencies) * 0.99)]

        print(
            f"\n[10K STRESS REPORT | 200 rooms | 4096-bit]\n"
            f"  False Negative Rate : {fn_rate:.2f}% ({false_negatives}/{len(known_queries)})\n"
            f"  False Positive Rate : {fp_rate:.2f}% ({false_positives}/{len(unknown_queries)})\n"
            f"  Avg Latency         : {avg_us:.2f} us\n"
            f"  P99 Latency         : {p99_us:.2f} us"
        )

        self.assertLess(fp_rate, 2.0, f"False positive rate too high: {fp_rate:.2f}%")
        self.assertLess(fn_rate, 15.0, f"False negative rate too high: {fn_rate:.2f}%")


if __name__ == "__main__":
    unittest.main()
