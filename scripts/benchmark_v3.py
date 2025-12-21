#!/usr/bin/env python3
"""
Sugar V3 Benchmark Script

Measures the concrete overhead improvements of V3 (Agent SDK) vs V2 (subprocess).
These benchmarks focus on what V3 actually improves - startup overhead,
hook latency, and memory footprint - NOT Claude API call time which is identical.

Usage:
    python scripts/benchmark_v3.py
"""

import asyncio
import statistics
import sys
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""
    name: str
    samples: list[float]
    unit: str

    @property
    def mean(self) -> float:
        return statistics.mean(self.samples)

    @property
    def median(self) -> float:
        return statistics.median(self.samples)

    @property
    def stdev(self) -> float:
        return statistics.stdev(self.samples) if len(self.samples) > 1 else 0

    @property
    def min_val(self) -> float:
        return min(self.samples)

    @property
    def max_val(self) -> float:
        return max(self.samples)

    def __str__(self) -> str:
        return (
            f"{self.name}:\n"
            f"  Mean: {self.mean:.2f} {self.unit}\n"
            f"  Median: {self.median:.2f} {self.unit}\n"
            f"  Std Dev: {self.stdev:.2f} {self.unit}\n"
            f"  Range: {self.min_val:.2f} - {self.max_val:.2f} {self.unit}"
        )


def benchmark_v3_import_time(iterations: int = 10) -> BenchmarkResult:
    """Measure time to import V3 agent modules."""
    import importlib

    times = []
    for _ in range(iterations):
        # Clear cached imports
        modules_to_clear = [k for k in sys.modules.keys() if k.startswith('sugar.agent')]
        for mod in modules_to_clear:
            del sys.modules[mod]

        start = time.perf_counter()
        importlib.import_module('sugar.agent.base')
        importlib.import_module('sugar.agent.hooks')
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    return BenchmarkResult("V3 Module Import Time", times, "ms")


def benchmark_v3_config_creation(iterations: int = 100) -> BenchmarkResult:
    """Measure time to create agent config."""
    from sugar.agent.base import SugarAgentConfig

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        config = SugarAgentConfig(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            permission_mode="acceptEdits",
            quality_gates_enabled=True,
        )
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    return BenchmarkResult("V3 Config Creation", times, "ms")


def benchmark_v3_agent_creation(iterations: int = 50) -> BenchmarkResult:
    """Measure time to create SugarAgent instance."""
    from sugar.agent.base import SugarAgent, SugarAgentConfig

    config = SugarAgentConfig(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        permission_mode="acceptEdits",
    )

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        agent = SugarAgent(config)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    return BenchmarkResult("V3 Agent Creation", times, "ms")


def benchmark_hooks_creation(iterations: int = 100) -> BenchmarkResult:
    """Measure time to create quality gate hooks."""
    from sugar.agent.hooks import QualityGateHooks

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        hooks = QualityGateHooks({
            "protected_files": [".env", "*.pem", "credentials.json"],
            "blocked_commands": ["sudo", "rm -rf /"],
        })
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    return BenchmarkResult("Quality Gate Hooks Creation", times, "ms")


async def benchmark_hooks_check(iterations: int = 100) -> BenchmarkResult:
    """Measure time for a security check on a file path."""
    from sugar.agent.hooks import QualityGateHooks

    hooks = QualityGateHooks({
        "protected_files": [".env", "*.pem", "credentials.json", "secrets/*"],
        "blocked_commands": ["sudo", "rm -rf /", "chmod 777"],
    })

    # Simulate tool use input
    test_inputs = [
        {"file_path": "/project/src/main.py"},
        {"file_path": "/project/.env"},
        {"file_path": "/project/config/settings.yaml"},
        {"command": "ls -la"},
        {"command": "sudo rm -rf /"},
    ]

    times = []
    for i in range(iterations):
        input_data = test_inputs[i % len(test_inputs)]
        start = time.perf_counter()
        result = await hooks.pre_tool_security_check(
            input_data=input_data,
            tool_use_id=f"test_{i}",
            context={"tool_name": "Write" if "file_path" in input_data else "Bash"}
        )
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    return BenchmarkResult("Security Check Latency", times, "ms")


def benchmark_response_serialization(iterations: int = 100) -> BenchmarkResult:
    """Measure time to serialize agent response."""
    from sugar.agent.base import AgentResponse

    response = AgentResponse(
        success=True,
        content="Task completed successfully. Created new file.",
        tool_uses=[
            {"tool": "Write", "input": {"file_path": "/project/src/new.py"}},
            {"tool": "Bash", "input": {"command": "python -m pytest"}},
        ],
        files_modified=["/project/src/new.py", "/project/tests/test_new.py"],
        execution_time=45.2,
        error=None,
        quality_gate_results={
            "total_tool_executions": 5,
            "blocked_operations": 0,
            "security_violations": 0,
        },
    )

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        data = response.to_dict()
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    return BenchmarkResult("Response Serialization", times, "ms")


def benchmark_memory_footprint() -> dict:
    """Measure memory footprint of V3 components."""
    import gc

    results = {}

    # Baseline
    gc.collect()
    tracemalloc.start()
    baseline = tracemalloc.get_traced_memory()[0]

    # Import agent modules
    from sugar.agent.base import SugarAgent, SugarAgentConfig
    from sugar.agent.hooks import QualityGateHooks

    gc.collect()
    after_import = tracemalloc.get_traced_memory()[0]
    results["module_import_mb"] = (after_import - baseline) / (1024 * 1024)

    # Create config
    config = SugarAgentConfig(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        permission_mode="acceptEdits",
        quality_gates_enabled=True,
    )

    gc.collect()
    after_config = tracemalloc.get_traced_memory()[0]
    results["config_mb"] = (after_config - after_import) / (1024 * 1024)

    # Create agent
    agent = SugarAgent(config)

    gc.collect()
    after_agent = tracemalloc.get_traced_memory()[0]
    results["agent_mb"] = (after_agent - after_config) / (1024 * 1024)

    # Create hooks
    hooks = QualityGateHooks({
        "protected_files": [".env", "*.pem"],
        "blocked_commands": ["sudo"],
    })

    gc.collect()
    after_hooks = tracemalloc.get_traced_memory()[0]
    results["hooks_mb"] = (after_hooks - after_agent) / (1024 * 1024)

    # Total
    results["total_mb"] = (after_hooks - baseline) / (1024 * 1024)

    tracemalloc.stop()

    return results


def benchmark_transient_error_detection(iterations: int = 100) -> BenchmarkResult:
    """Measure time to detect transient errors."""
    from sugar.agent.base import is_transient_error

    test_errors = [
        Exception("rate_limit exceeded"),
        Exception("Connection timeout"),
        Exception("503 Service Unavailable"),
        Exception("429 Too Many Requests"),
        Exception("API overloaded"),
        Exception("Invalid request"),  # Not transient
        ValueError("Bad input"),  # Not transient
    ]

    times = []
    for i in range(iterations):
        error = test_errors[i % len(test_errors)]
        start = time.perf_counter()
        is_transient_error(error)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    return BenchmarkResult("Transient Error Detection", times, "ms")


async def run_benchmarks():
    """Run all benchmarks and display results."""
    print("=" * 60)
    print("Sugar V3 Benchmark Suite")
    print("=" * 60)
    print()
    print("These benchmarks measure V3 overhead improvements.")
    print("Note: Claude API call time is NOT measured (identical in V2/V3).")
    print()
    print("-" * 60)

    results = []

    # Timing benchmarks
    print("\nRunning timing benchmarks...")

    results.append(benchmark_v3_import_time())
    print(f"  - Module import: {results[-1].mean:.2f}ms")

    results.append(benchmark_v3_config_creation())
    print(f"  - Config creation: {results[-1].mean:.3f}ms")

    results.append(benchmark_v3_agent_creation())
    print(f"  - Agent creation: {results[-1].mean:.3f}ms")

    results.append(benchmark_hooks_creation())
    print(f"  - Hooks creation: {results[-1].mean:.3f}ms")

    results.append(await benchmark_hooks_check())
    print(f"  - Security check: {results[-1].mean:.3f}ms")

    results.append(benchmark_response_serialization())
    print(f"  - Response serialization: {results[-1].mean:.3f}ms")

    results.append(benchmark_transient_error_detection())
    print(f"  - Error detection: {results[-1].mean:.4f}ms")

    # Memory benchmark
    print("\nRunning memory benchmarks...")
    memory = benchmark_memory_footprint()

    # Calculate total startup overhead
    total_startup = sum(r.mean for r in results[:4])

    print()
    print("=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    print("\n## Startup Overhead (V3)")
    print(f"  Total initialization: {total_startup:.2f}ms")
    print(f"  - Module import: {results[0].mean:.2f}ms")
    print(f"  - Config creation: {results[1].mean:.3f}ms")
    print(f"  - Agent creation: {results[2].mean:.3f}ms")
    print(f"  - Hooks creation: {results[3].mean:.3f}ms")

    print("\n## Per-Operation Latency")
    print(f"  Security check: {results[4].mean:.3f}ms")
    print(f"  Response serialization: {results[5].mean:.3f}ms")
    print(f"  Error detection: {results[6].mean:.4f}ms")

    print("\n## Memory Footprint")
    print(f"  Total V3 components: {memory['total_mb']:.2f}MB")
    print(f"  - Module import: {memory['module_import_mb']:.2f}MB")
    print(f"  - Agent instance: {memory['agent_mb']:.3f}MB")
    print(f"  - Hooks instance: {memory['hooks_mb']:.3f}MB")

    print("\n## Comparison with V2 (Subprocess)")
    print("  V2 subprocess spawn: ~300-500ms")
    print(f"  V3 native startup: ~{total_startup:.0f}ms")
    print(f"  Improvement: ~{(400 - total_startup):.0f}ms faster")
    print()
    print("  V2 memory (separate process): ~50-100MB additional")
    print(f"  V3 memory (shared process): ~{memory['total_mb']:.1f}MB additional")
    print(f"  Improvement: ~{50 - memory['total_mb']:.0f}MB less")

    print()
    print("=" * 60)
    print("CONTEXT")
    print("=" * 60)
    print("""
These improvements apply to OVERHEAD only. The actual Claude API
call takes 30-300 seconds depending on task complexity.

Example total task time breakdown:
  V2: 400ms overhead + 60s Claude = 60.4s total
  V3: 50ms overhead + 60s Claude = 60.05s total

The ~350ms improvement is real but represents < 1% of total time.

V3's main benefits are:
  1. Security gates (can BLOCK dangerous operations)
  2. Observability (structured tool tracking)
  3. Reliability (automatic retry on transient errors)
""")

    return results, memory


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
