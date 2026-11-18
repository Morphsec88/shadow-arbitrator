# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Morphsec88

import unittest
from arbitrator.encoder import BitEncoder, popcount


class TestBitEncoder(unittest.TestCase):
    def setUp(self):
        self.encoder = BitEncoder(width=1024)

    def test_determinism(self):
        v1 = self.encoder.encode("quantum cryptography")
        v2 = self.encoder.encode("  QUANTUM CRYPTOGRAPHY! ")
        self.assertEqual(v1, v2)
        self.assertGreater(popcount(v1), 0)

    def test_orthogonality(self):
        v1 = self.encoder.encode("processor register bitwise operation")
        v2 = self.encoder.encode("sourdough pickle recipe")
        overlap = popcount(v1 & v2) / max(1, popcount(v1))
        self.assertLess(overlap, 0.25)


if __name__ == "__main__":
    unittest.main()
