# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Morphsec88

import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from arbitrator.encoder import BitEncoder
from arbitrator.engine import ArbitratorEngine
from arbitrator.filter import DecisionType, HallwayFilter
from arbitrator.module import ComputeModule


class DomainKnowledgeBase:
    """Stores fast-path and deep-compute responses for registered modules."""

    def __init__(self) -> None:
        self.fast_responses: Dict[int, str] = {}
        self.deep_responses: Dict[int, str] = {}

    def register(
        self,
        engine: ArbitratorEngine,
        mod_id: int,
        domain: str,
        patterns: List[str],
        fast_reply: str,
        deep_reply: str,
    ) -> None:
        mod = ComputeModule(mod_id, domain, engine.encoder)
        mod.ingest_patterns(patterns)
        engine.register_module(mod)
        self.fast_responses[mod_id] = fast_reply
        self.deep_responses[mod_id] = deep_reply


def setup_demo_system(total_modules: int = 250) -> Tuple[ArbitratorEngine, DomainKnowledgeBase]:
    random.seed(88)
    encoder = BitEncoder(width=1024)
    hallway_filter = HallwayFilter(vector_width=1024)
    engine = ArbitratorEngine(encoder=encoder, hallway_filter=hallway_filter)
    kb = DomainKnowledgeBase()

    specialists = [
        (
            0,
            "routine_greeting",
            ["hello", "hi", "good morning", "greetings", "hey"],
            "Hello! System ready.",
            "Hello! Full diagnostics report: all compute modules nominal.",
        ),
        (
            1,
            "hardware_cpu",
            ["processor clock", "bitwise operation", "register", "cpu", "memory"],
            "Hardware execution: native 64-bit AND/XOR and POPCNT instructions.",
            "Deep hardware analysis: L1-resident bitvectors minimize memory bandwidth overhead.",
        ),
        (
            2,
            "cryptography",
            ["encryption", "hash algorithm", "public key", "cryptography", "blake2b"],
            "Cryptography: deterministic BLAKE2b projection and orthogonal masks.",
            "Deep cryptographic analysis: LSH collision resistance scales with vector width.",
        ),
        (
            3,
            "network_dsp",
            ["signal processing", "interference", "filter", "entropy", "broadcast"],
            "DSP Filter: constructive interference and entropy gating active.",
            "Deep DSP analysis: dynamic noise-floor compensation suppresses statistical collisions.",
        ),
        (
            4,
            "noise_hallucinator",
            ["processor banana", "encryption potato"],
            "[NOISE MODULE - MUST BE SUPPRESSED]",
            "Isolated false association.",
        ),
    ]

    for mod_id, domain, patterns, fast_r, deep_r in specialists:
        kb.register(engine, mod_id, domain, patterns, fast_r, deep_r)

    filler_vocab = [
        "protocol", "interface", "packet", "buffer", "cycle",
        "state", "transaction", "thread", "scheduler", "channel",
    ]
    for mod_id in range(len(specialists), total_modules):
        samples = [
            f"{random.choice(filler_vocab)} {random.choice(filler_vocab)} {mod_id}"
            for _ in range(3)
        ]
        kb.register(
            engine,
            mod_id,
            f"background_domain_{mod_id}",
            samples,
            f"Background module #{mod_id} fast response.",
            f"Background module #{mod_id} deep compute analysis.",
        )

    return engine, kb


def print_execution(engine: ArbitratorEngine, kb: DomainKnowledgeBase, query: str) -> None:
    report = engine.process(query)
    dec = report.decision

    print(f"Input        : {query}")
    print(f"Decision     : {dec.decision.value.upper()}")
    print(
        f"Metrics      : Sharpness={dec.top_sharpness:.1%} | Noise={dec.noise_floor:.1%} | "
        f"Consensus={dec.consensus_confidence:.1%} (Threshold: {dec.effective_vote_threshold} votes)"
    )
    print(
        f"Compute      : {report.woken_modules} / {report.total_modules} modules woken "
        f"({100 - (report.woken_modules / report.total_modules * 100):.1f}% saved)"
    )
    print(f"Latency      : {report.latency_us:.2f} us")

    if dec.decision == DecisionType.SHORT_CIRCUIT:
        mod = dec.selected_modules[0]
        print(f"Output       : [{mod.domain}] {kb.fast_responses[mod.module_id]}")

    elif dec.decision == DecisionType.CONSTRUCTIVE_INTERFERENCE:
        print("Output       : (Constructive shadow interference)")
        for mod in dec.selected_modules:
            print(f"               - [{mod.domain}] {kb.fast_responses[mod.module_id]}")

    elif dec.decision == DecisionType.CONFIDENCE_GATE:
        print("Output       : (Confidence Gate -> Selective deep compute)")
        for mod in dec.selected_modules:
            print(f"               - [{mod.domain}] {kb.deep_responses[mod.module_id]}")

    else:
        print("Output       : Empty or unresolvable input signal.")

    print("-" * 78)


def main() -> None:
    engine, kb = setup_demo_system(total_modules=250)

    print("=" * 78)
    print("SHADOW ARBITRATOR - DETERMINISTIC DSP INTERFERENCE DEMO (250 MODULES)")
    print("Copyright (C) 2026 Morphsec88 | License: AGPL-3.0-or-later")
    print("=" * 78)

    sample_queries = [
        "Hello!",
        "processor encryption signal processing",
        "how to ferment cucumbers for winter storage",
    ]

    for q in sample_queries:
        print_execution(engine, kb, q)

    print("Interactive mode (type 'exit' or press Enter on an empty line to quit):")
    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input or user_input.lower() in {"exit", "quit"}:
            break
        print_execution(engine, kb, user_input)


if __name__ == "__main__":
    main()
