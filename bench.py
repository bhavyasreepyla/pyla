#!/usr/bin/env python3
"""Benchmark: tree-walking evaluator vs bytecode VM.

Runs the same Pyla programs on both engines and reports wall-clock time.
"""

import time

from pyla import run
from pyla.vm import vm_run

BENCHMARKS = {
    "fib(22) recursive": """
        let fib = fn(n) { if (n < 2) { n } else { fib(n-1) + fib(n-2) } };
        fib(22)
    """,
    "loop: sum 1..300000": """
        let s = 0;
        let i = 0;
        while (i < 300000) { i = i + 1; s = s + i; }
        s
    """,
    "closures: 100k counter calls": """
        let make = fn() { let n = 0; fn() { n = n + 1; n } };
        let c = make();
        for (let i = 0; i < 100000; i = i + 1) { c(); }
        c()
    """,
    "arrays: build + index 50k": """
        let a = [];
        for (let i = 0; i < 50000; i = i + 1) { push(a, i * 2); }
        let s = 0;
        for (let i = 0; i < 50000; i = i + 1) { s = s + a[i]; }
        s
    """,
}


def time_engine(fn, source):
    start = time.perf_counter()
    result = fn(source)
    elapsed = time.perf_counter() - start
    return elapsed, result


def main():
    print(f"{'benchmark':<32} {'tree-walker':>12} {'bytecode VM':>12} {'speedup':>9}")
    print("-" * 69)
    for name, source in BENCHMARKS.items():
        tree_time, tree_result = time_engine(run, source)
        vm_time, vm_result = time_engine(vm_run, source)
        assert tree_result.inspect() == vm_result.inspect(), \
            f"engines disagree on {name}!"
        speedup = tree_time / vm_time if vm_time else float("inf")
        print(f"{name:<32} {tree_time:>10.3f}s {vm_time:>10.3f}s {speedup:>8.2f}x")
    print("\n(identical results verified on every benchmark)")


if __name__ == "__main__":
    main()
