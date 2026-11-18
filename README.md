# shadow-arbitrator

Deterministic bitwise routing and shadow arbitration engine for modular systems.

`shadow-arbitrator` routes incoming queries without vector embeddings, matrix multiplications, or waking dormant compute modules. Input text is projected into a 4096-bit N-gram mask and evaluated across isolated modules (`ComputeModule`) via single-cycle bitwise intersections (`&`). Routing decisions are computed using contender-sparsity gating and Z-score normalization.

- **Zero external dependencies:** Uses only the Python 3.10+ standard library (`hashlib`, `math`, `struct`, `re`, `dataclasses`, `enum`).
- **Deterministic routing:** Decisions (`short_circuit`, `constructive_interference`, `confidence_gate`) are reproducible and directly traceable to bit-level intersections.
- **Saturation resistance:** Frequency-pruned bitmasks cap bit density during ingestion (`max_density = 0.20`), preventing Bloom OR-saturation under heavy pattern loads.

## Architecture

1. **BitEncoder (`src/arbitrator/encoder.py`)**
   Normalizes input strings, strips common stopwords, and hashes character N-grams via BLAKE2b into a fixed-width 4096-bit integer.

2. **ComputeModule (`src/arbitrator/module.py`)**
   Maintains a static, sparsity-bounded `knowledge_mask` per domain. During `ingest_patterns`, bit activation counts are tracked and pruned to the top 20% most frequent bits. Incoming queries are evaluated via `aligned_signal & knowledge_mask` without activating module compute payloads.

3. **HallwayFilter (`src/arbitrator/filter.py`)**
   - **Contender Gating:** Uses a bit-sliced carry-save counter (`_bits_at_least_k`) to detect bits claimed by too many modules simultaneously. Over-crowded background bits are masked out (`~crowded_bits`), leaving only high-specificity matches.
   - **Z-Score Normalization:** Calculates mean (μ) and standard deviation (σ) across all module shadow energies (\(Z_i = \frac{E_i - \mu}{\sigma}\)), keeping thresholds invariant to query length and module count. *(Note: The default `z_short_circuit = 3.2` threshold is calibrated for 12+ active modules; for smaller setups with 3–10 modules, lower `z_short_circuit` to ~`1.5`–`2.2`.)*
   - **Decision Tiers:**
     - `short_circuit`: Single statistical outlier (\(Z_{top} \ge 3.2\) with runner-up margin ≥ 1.0). Wakes 0 modules.
     - `constructive_interference`: Bit-sliced consensus across multiple elevated contenders while cancelling uncorrelated noise. Wakes 0 modules.
     - `confidence_gate`: Fallback when no statistically significant match exists; selectively wakes up to `max_wake_modules` (default: 3).

## Benchmarks

Tested single-threaded on a Lenovo IdeaPad 100 (Windows CMD, Python 3.14.5, zero C extensions).

### 10,000-Query Stress Test (`tests/test_stress.py`)

Evaluated across 200 modules (including an adversarial module trained on 300 generic filler samples) using 4,000 known/noisy queries (35% character-level typo injection) and 6,000 out-of-domain queries:

| Metric | Result |
| :--- | :--- |
| Vector Width | 4096-bit |
| Active Modules | 200 |
| False Negative Rate (4,000 known/noisy) | 0.00% (0 / 4,000) |
| False Positive Rate (6,000 unknown) | 0.00% (0 / 6,000) |
| Average Latency | 2.72 ms (2,715.40 us) |
| P99 Latency | 4.46 ms (4,456.80 us) |

### Routine Query Scaling (`benchmarks/run_bench.py`)

| Modules | Routine Query Avg | P99 Latency | Woken Modules |
| :--- | :--- | :--- | :--- |
| 100 | 673.49 us | 969.00 us | 0 |
| 1,000 | 5.26 ms (5,263.86 us) | 5.93 ms | 0 |

## Usage

```python
from arbitrator.encoder import BitEncoder
from arbitrator.engine import ArbitratorEngine
from arbitrator.filter import HallwayFilter
from arbitrator.module import ComputeModule

encoder = BitEncoder(width=4096)
# For small module counts (< 12), lower z_short_circuit (e.g. 1.2)
engine = ArbitratorEngine(
    encoder=encoder,
    hallway_filter=HallwayFilter(vector_width=4096, z_short_circuit=1.2)
)

crypto = ComputeModule(0, "cryptography", encoder)
crypto.ingest_patterns(["elliptic curve", "aes cipher", "merkle tree", "zero knowledge proof"])
engine.register_module(crypto)

kernel = ComputeModule(1, "kernel_memory", encoder)
kernel.ingest_patterns(["page fault", "virtual memory", "spinlock mutex", "syscall interrupt"])
engine.register_module(kernel)

report = engine.process("zero knowledge proof")
print(report.decision.decision.value)          # short_circuit
print(report.decision.selected_modules[0].domain)  # cryptography
print(report.woken_modules)                    # 0
```

## Running Tests

```cmd
set PYTHONPATH=src
python -m unittest discover -s tests -v
python benchmarks/run_bench.py
```

## License

Copyright (C) 2026 Morphsec88  
Licensed under the GNU Affero General Public License v3.0 or later (`AGPL-3.0-or-later`).
