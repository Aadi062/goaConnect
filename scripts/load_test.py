"""
GoaConnect Load Test — measures API performance baseline.
Run: python scripts/load_test.py
Results saved to: scripts/benchmark_results.json
"""
import asyncio
import json
import time
import statistics
from typing import List
import httpx

BASE_URL = "http://localhost:8000"
CONCURRENT = 20
ITERATIONS = 100


async def measure_endpoint(client: httpx.AsyncClient, path: str, method: str = "GET", **kwargs) -> float:
    start = time.perf_counter()
    r = await client.request(method, f"{BASE_URL}{path}", **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return elapsed_ms, r.status_code


async def run_load_test(path: str, n: int = CONCURRENT, method: str = "GET", **kwargs) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [measure_endpoint(client, path, method, **kwargs) for _ in range(n)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    latencies = [r[0] for r in results if isinstance(r, tuple) and r[1] < 500]
    errors = sum(1 for r in results if isinstance(r, Exception) or (isinstance(r, tuple) and r[1] >= 500))

    if not latencies:
        return {"error": "all_requests_failed", "path": path}

    return {
        "path": path,
        "n": n,
        "p50_ms": round(statistics.median(latencies), 2),
        "p95_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 2),
        "p99_ms": round(sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) >= 100 else max(latencies), 2),
        "mean_ms": round(statistics.mean(latencies), 2),
        "min_ms": round(min(latencies), 2),
        "max_ms": round(max(latencies), 2),
        "errors": errors,
        "success_rate": f"{round((len(latencies) / n) * 100, 1)}%",
    }


async def main():
    print("GoaConnect API Load Test")
    print("=" * 60)

    results = []
    tests = [
        ("/health", "GET"),
        ("/ready", "GET"),
        ("/api/v1/tourism/places", "GET"),
    ]

    for path, method in tests:
        print(f"Testing {method} {path}...")
        result = await run_load_test(path, CONCURRENT, method)
        results.append(result)
        print(f"  p50={result.get('p50_ms')}ms p95={result.get('p95_ms')}ms errors={result.get('errors')}")

    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "configuration": {"concurrent": CONCURRENT, "iterations_per_test": CONCURRENT},
        "results": results,
        "note": "Baseline measurement — compare after optimizations",
    }

    with open("scripts/benchmark_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n✓ Results saved to scripts/benchmark_results.json")


if __name__ == "__main__":
    asyncio.run(main())
