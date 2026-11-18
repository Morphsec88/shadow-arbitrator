# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Morphsec88

import unittest
from arbitrator.encoder import BitEncoder, popcount
from arbitrator.engine import ArbitratorEngine
from arbitrator.filter import DecisionType, HallwayFilter
from arbitrator.module import ComputeModule


class TestHallwayFilter(unittest.TestCase):
    def setUp(self):
        self.encoder = BitEncoder(width=4096)
        hallway_filter = HallwayFilter(
            vector_width=4096,
            z_short_circuit=2.2,
            min_raw_sharpness=0.40,
            min_consensus_votes=2,
            confidence_threshold=0.40,
        )
        self.engine = ArbitratorEngine(encoder=self.encoder, hallway_filter=hallway_filter)

        m0 = ComputeModule(0, "greeting", self.encoder)
        m0.ingest_patterns(["hello", "hi", "good morning", "greetings"])

        m1 = ComputeModule(1, "quantum_crypto", self.encoder)
        m1.ingest_patterns(["quantum key", "quantum encryption", "photon"])

        m2 = ComputeModule(2, "applied_crypto", self.encoder)
        m2.ingest_patterns(["encryption algorithm", "quantum encryption", "hash"])

        m3 = ComputeModule(3, "hallucinator", self.encoder)
        m3.ingest_patterns(["quantum banana", "photon potato"])

        # Add background rooms so Z-score statistics reflect realistic multi-room competition
        for idx in range(4, 15):
            bg = ComputeModule(idx, f"background_{idx}", self.encoder)
            bg.ingest_patterns([f"network packet protocol {idx}", f"memory buffer register {idx}"])
            self.engine.register_module(bg)

        for m in (m0, m1, m2, m3):
            self.engine.register_module(m)

    def test_short_circuit(self):
        report = self.engine.process("Hello!")
        self.assertEqual(report.decision.decision, DecisionType.SHORT_CIRCUIT)
        self.assertEqual(report.woken_modules, 0)
        self.assertEqual(report.decision.selected_modules[0].domain, "greeting")

    def test_constructive_interference_and_noise_cancellation(self):
        report = self.engine.process("quantum encryption")
        self.assertEqual(report.decision.decision, DecisionType.CONSTRUCTIVE_INTERFERENCE)
        self.assertEqual(report.woken_modules, 0)

        noise_vec = self.encoder.encode("banana potato")
        consensus_overlap = popcount(report.decision.consensus_vector & noise_vec)
        self.assertLessEqual(consensus_overlap, 2)

    def test_confidence_gate(self):
        report = self.engine.process("how to ferment cucumbers for winter")
        self.assertEqual(report.decision.decision, DecisionType.CONFIDENCE_GATE)
        self.assertGreater(report.woken_modules, 0)

    def test_saturation_resistance(self):
        overfed = ComputeModule(99, "overfed_room", self.encoder, max_density=0.20)
        overfed.ingest_patterns([f"generic random filler sentence number {i} with many words" for i in range(200)])
        self.assertLessEqual(overfed.mask_density, 0.21)


if __name__ == "__main__":
    unittest.main()
