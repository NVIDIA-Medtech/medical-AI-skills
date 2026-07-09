# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Lightweight progress telemetry for the curation eval harness.

All telemetry is written to **stderr** (with elapsed-time stamps and flushing)
so that the final machine-readable JSON on stdout stays clean, and progress
streams live to the terminal during long remote runs.
"""

from __future__ import annotations

import sys
import threading
import time

_state = {
    "verbose": True,
    "t0": time.perf_counter(),
    "calls": 0,
    "tokens": 0,
}
_lock = threading.Lock()


def configure(verbose: bool = True) -> None:
    _state["verbose"] = verbose
    _state["t0"] = time.perf_counter()
    _state["calls"] = 0
    _state["tokens"] = 0


def _stamp() -> str:
    return f"{time.perf_counter() - _state['t0']:7.1f}s"


def log(msg: str) -> None:
    """Emit a timestamped telemetry line to stderr."""
    if not _state["verbose"]:
        return
    print(f"[ceval {_stamp()}] {msg}", file=sys.stderr, flush=True)


def rule(msg: str) -> None:
    """Emit a visually separated section header."""
    if not _state["verbose"]:
        return
    print(f"[ceval {_stamp()}] {'=' * 3} {msg} {'=' * 3}", file=sys.stderr, flush=True)


def call_tick(step: str, arm: str, i: int, n: int, ok: bool,
              latency_s: float, tokens: int) -> None:
    """Report one LLM call's outcome plus running study-wide totals."""
    with _lock:
        _state["calls"] += 1
        _state["tokens"] += int(tokens or 0)
        total_calls = _state["calls"]
        total_tokens = _state["tokens"]
    if not _state["verbose"]:
        return
    status = "ok " if ok else "FAIL"
    bar = _progress_bar(i, n)
    print(
        f"[ceval {_stamp()}]   {step:<6} {arm:<7} {bar} {i:>2}/{n} {status} "
        f"{latency_s:5.1f}s {int(tokens or 0):>5}tok  "
        f"(run: {total_calls} calls / {total_tokens} tok)",
        file=sys.stderr,
        flush=True,
    )


def _progress_bar(i: int, n: int, width: int = 10) -> str:
    if n <= 0:
        return "[" + " " * width + "]"
    filled = int(round(width * i / n))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def totals() -> dict:
    with _lock:
        return {"calls": _state["calls"], "tokens": _state["tokens"],
                "elapsed_s": round(time.perf_counter() - _state["t0"], 1)}
