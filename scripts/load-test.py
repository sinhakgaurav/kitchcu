#!/usr/bin/env python3
"""Light load test against CKAC gateway — health, kitchens, menus."""

from __future__ import annotations

import concurrent.futures
import os
import statistics
import time
import urllib.error
import urllib.request

GATEWAY = os.environ.get("CKAC_GATEWAY_URL", "http://localhost:18000").rstrip("/")
REQUESTS = int(os.environ.get("CKAC_LOAD_REQUESTS", "100"))
WORKERS = int(os.environ.get("CKAC_LOAD_WORKERS", "10"))


def fetch(path: str) -> tuple[float, int]:
    url = f"{GATEWAY}{path}"
    start = time.perf_counter()
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()
        code = resp.status
    return time.perf_counter() - start, code


def run_batch(path: str, n: int) -> None:
    latencies: list[float] = []
    errors = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(fetch, path) for _ in range(n)]
        for fut in concurrent.futures.as_completed(futures):
            try:
                lat, code = fut.result()
                if code >= 400:
                    errors += 1
                else:
                    latencies.append(lat)
            except (urllib.error.URLError, TimeoutError):
                errors += 1

    if latencies:
        p50 = statistics.median(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95) - 1]
        print(
            f"{path}: {len(latencies)}/{n} ok | p50={p50*1000:.0f}ms p95={p95*1000:.0f}ms | errors={errors}"
        )
    else:
        print(f"{path}: all failed ({errors} errors)")


def main() -> None:
    print(f"Load test -> {GATEWAY} ({REQUESTS} req x {WORKERS} workers)")
    run_batch("/health/ready", REQUESTS)
    run_batch("/api/v1/kitchens/public/nearby?latitude=18.5362&longitude=73.8958&limit=20", REQUESTS)


if __name__ == "__main__":
    main()
