"""Capture wall / CPU / RSS / GPU cost around a subprocess.

The cost gate is the eval_engine's domain-neutral verifier: a skill that
claims to do X must consume cost-Y and produce output-Z. Cost is
observable from outside the skill -- the skill cannot fake having
spent compute it did not spend -- so an empty-output silent failure
(13 ms instead of 30 s) or a "free-rider" skill that returned plausible
JSON without actually invoking the model both fall outside their
declared envelope.

Usage::

    with CostCapture() as cc:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    profile = cc.profile()        # dict ready to write to cost_profile.json

The capture is best-effort: psutil and nvidia-smi may be missing on a
host. The profile dict records `have_psutil` and `have_nvidia_smi` so
downstream readers can tell which fields are populated and which are
zero because the tool was unavailable.
"""
from __future__ import annotations

import os
import resource
import shutil
import subprocess
import threading
import time
from typing import Any


class CostCapture:
    """Best-effort wall / CPU / RSS / GPU cost capture for a subprocess run.

    Wall and CPU time + max RSS come from `resource.getrusage(RUSAGE_CHILDREN)`;
    GPU utilisation and memory come from polling `nvidia-smi` in a background
    thread for the duration of the `with` block. Samples are attributed only
    when `nvidia-smi` reports a compute app owned by a descendant process of
    this runner, so CPU-only skills are not charged for unrelated GPU work on
    the same host. Time-integrated GPU seconds are reported as
    `avg_util_pct/100 * wall_seconds` per device, so a run that holds a GPU
    for 30 s at 80% reports `gpu_seconds=24`.
    """

    DEFAULT_GPU_POLL_MS = 100

    def __init__(self, gpu_poll_ms: int = DEFAULT_GPU_POLL_MS):
        self._gpu_poll_ms = gpu_poll_ms
        self._t_start: float = 0.0
        self._t_end: float = 0.0
        self._u0 = self._u1 = 0.0
        self._s0 = self._s1 = 0.0
        self._rss0_kb = self._rss1_kb = 0
        self._gpu_thread: threading.Thread | None = None
        self._gpu_stop = threading.Event()
        self._gpu_samples: list[dict[str, Any]] = []
        self._have_nvidia_smi = bool(shutil.which("nvidia-smi"))

    @staticmethod
    def _rusage() -> tuple[float, float, int]:
        r = resource.getrusage(resource.RUSAGE_CHILDREN)
        return r.ru_utime, r.ru_stime, r.ru_maxrss

    @staticmethod
    def _descendant_pids(root_pid: int) -> set[int]:
        """Return current Linux descendant PIDs for `root_pid`.

        Keep this stdlib-only; psutil is intentionally not required for the
        evaluation engine. If /proc is unavailable, return an empty set and
        GPU attribution simply records no process-owned samples.
        """
        parent_by_pid: dict[int, int] = {}
        try:
            proc_names = os.listdir("/proc")
        except OSError:
            return set()
        for name in proc_names:
            if not name.isdigit():
                continue
            pid = int(name)
            try:
                with open(f"/proc/{pid}/stat", encoding="utf-8") as f:
                    stat = f.read()
            except OSError:
                continue
            rparen = stat.rfind(")")
            if rparen == -1:
                continue
            fields = stat[rparen + 1:].split()
            if len(fields) < 2:
                continue
            try:
                parent_by_pid[pid] = int(fields[1])
            except ValueError:
                continue

        descendants: set[int] = set()
        changed = True
        while changed:
            changed = False
            for pid, ppid in parent_by_pid.items():
                if pid in descendants:
                    continue
                if ppid == root_pid or ppid in descendants:
                    descendants.add(pid)
                    changed = True
        return descendants

    def __enter__(self) -> "CostCapture":
        self._u0, self._s0, self._rss0_kb = self._rusage()
        self._t_start = time.monotonic()
        # Baseline GPU memory snapshot. Subtracted from peak in profile() so
        # the reported gpu_memory_mb_peak attributes only this skill's
        # allocation, not whatever else is resident on the GPU.
        self._gpu_mem_baseline_mb: dict[int, float] = {}
        if self._have_nvidia_smi:
            try:
                out = subprocess.check_output(
                    ["nvidia-smi",
                     "--query-gpu=index,memory.used",
                     "--format=csv,noheader,nounits"],
                    text=True, timeout=2.0,
                )
                for line in out.strip().splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 2:
                        try:
                            self._gpu_mem_baseline_mb[int(parts[0])] = float(parts[1])
                        except ValueError:
                            continue
            except Exception:
                pass
            self._gpu_stop.clear()
            self._gpu_thread = threading.Thread(target=self._poll_gpu, daemon=True)
            self._gpu_thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._t_end = time.monotonic()
        if self._gpu_thread:
            self._gpu_stop.set()
            self._gpu_thread.join(timeout=2.0)
        self._u1, self._s1, self._rss1_kb = self._rusage()

    def _poll_gpu(self) -> None:
        gpu_cmd = [
            "nvidia-smi",
            "--query-gpu=index,uuid,utilization.gpu,memory.used",
            "--format=csv,noheader,nounits",
        ]
        app_cmd = [
            "nvidia-smi",
            "--query-compute-apps=pid,gpu_uuid,used_memory",
            "--format=csv,noheader,nounits",
        ]
        root_pid = os.getpid()
        while not self._gpu_stop.is_set():
            try:
                gpu_out = subprocess.check_output(gpu_cmd, text=True, timeout=2.0)
                ts = time.monotonic()
                gpu_by_uuid: dict[str, dict[str, float | int]] = {}
                for line in gpu_out.strip().splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) < 4:
                        continue
                    try:
                        gpu_by_uuid[parts[1]] = {
                            "index": int(parts[0]),
                            "util_pct": float(parts[2]),
                        }
                    except ValueError:
                        continue

                app_out = subprocess.check_output(app_cmd, text=True, timeout=2.0)
                descendant_pids = self._descendant_pids(root_pid)
                mem_by_gpu: dict[int, float] = {}
                for line in app_out.strip().splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) < 3:
                        continue
                    try:
                        pid = int(parts[0])
                        used_mb = float(parts[2])
                    except ValueError:
                        continue
                    if pid not in descendant_pids:
                        continue
                    gpu = gpu_by_uuid.get(parts[1])
                    if not gpu:
                        continue
                    gpu_idx = int(gpu["index"])
                    mem_by_gpu[gpu_idx] = mem_by_gpu.get(gpu_idx, 0.0) + used_mb

                for gpu in gpu_by_uuid.values():
                    gpu_idx = int(gpu["index"])
                    if gpu_idx not in mem_by_gpu:
                        continue
                    baseline = self._gpu_mem_baseline_mb.get(gpu_idx, 0.0)
                    self._gpu_samples.append({
                        "ts": ts,
                        "gpu": gpu_idx,
                        "util_pct": float(gpu["util_pct"]),
                        "mem_mb": baseline + mem_by_gpu[gpu_idx],
                    })
            except Exception:
                pass
            time.sleep(self._gpu_poll_ms / 1000.0)

    def profile(self) -> dict[str, Any]:
        wall_seconds = max(0.0, self._t_end - self._t_start)
        cpu_seconds = max(0.0, (self._u1 - self._u0) + (self._s1 - self._s0))
        # ru_maxrss is in KB on Linux and bytes on macOS; this repo targets
        # Linux runtimes (per AGENTS.md stack defaults), so KB is correct.
        rss_mb_peak = self._rss1_kb / 1024.0

        per_gpu: dict[str, dict[str, Any]] = {}
        gpu_seconds = 0.0
        gpu_memory_mb_peak = 0.0
        if self._gpu_samples:
            grouped: dict[int, dict[str, list[float]]] = {}
            for s in self._gpu_samples:
                g = grouped.setdefault(int(s["gpu"]), {"util": [], "mem": []})
                g["util"].append(float(s["util_pct"]))
                g["mem"].append(float(s["mem_mb"]))
            for gpu_idx, agg in grouped.items():
                avg_util_pct = sum(agg["util"]) / max(1, len(agg["util"]))
                mem_peak_abs = max(agg["mem"]) if agg["mem"] else 0.0
                baseline = self._gpu_mem_baseline_mb.get(gpu_idx, 0.0)
                # mem_mb_peak attributes only this skill's allocation:
                # absolute peak minus the GPU-resident baseline at __enter__.
                # Cannot go negative.
                mem_peak_delta = max(0.0, mem_peak_abs - baseline)
                seconds = (avg_util_pct / 100.0) * wall_seconds
                per_gpu[str(gpu_idx)] = {
                    "samples": len(agg["util"]),
                    "avg_util_pct": avg_util_pct,
                    "mem_mb_baseline": baseline,
                    "mem_mb_peak_abs": mem_peak_abs,
                    "mem_mb_peak": mem_peak_delta,
                    "gpu_seconds": seconds,
                }
                gpu_seconds = max(gpu_seconds, seconds)
                gpu_memory_mb_peak = max(gpu_memory_mb_peak, mem_peak_delta)

        return {
            "wall_seconds": wall_seconds,
            "cpu_seconds": cpu_seconds,
            "rss_mb_peak": rss_mb_peak,
            "gpu_seconds": gpu_seconds,
            "gpu_memory_mb_peak": gpu_memory_mb_peak,
            "per_gpu": per_gpu,
            "have_nvidia_smi": self._have_nvidia_smi,
        }


# Cost-envelope evaluator: mirrors the runtime / sanity gate style.
# A declared envelope looks like:
#   expected_cost:
#     wall_seconds:       {min: 5, max: 1800}
#     gpu_seconds:        {min: 1, max: 30}
#     gpu_memory_mb_peak: {min: 500, max: 14000}
#     rss_mb_peak:        {max: 16000}
#     llm_tokens_input:   {max: 0}
#     llm_tokens_output:  {max: 0}
# Any field absent from `declared` is skipped. Fields whose measured value
# is None (e.g. llm_tokens_* on a skill that did not self-report) are
# treated as 0 only if the declared envelope's `max` is 0; otherwise the
# field is reported as `skipped (not measured)` so a missing self-report
# doesn't silently pass.
def evaluate_cost_envelope(
    declared: dict[str, Any],
    measured: dict[str, Any],
    self_reported: dict[str, Any] | None = None,
) -> dict[str, Any]:
    self_reported = self_reported or {}
    results: list[dict[str, Any]] = []
    any_failed = False
    any_evaluated = False

    for key, bounds in (declared or {}).items():
        if not isinstance(bounds, dict):
            continue
        lo = bounds.get("min")
        hi = bounds.get("max")

        # Resolution order: eval_engine-measured (objective) first; if absent,
        # fall back to skill-self-reported (token costs etc.).
        if key in measured:
            actual = measured[key]
            source = "measured"
        elif key in self_reported:
            actual = self_reported[key]
            source = "self_reported"
        else:
            results.append({
                "key": key,
                "actual": None,
                "min": lo,
                "max": hi,
                "ok": False,
                "reason": "not measured and not self-reported",
                "source": "missing",
            })
            any_failed = True
            continue

        any_evaluated = True
        ok = True
        reason_parts: list[str] = []
        if lo is not None and actual < lo:
            ok = False
            reason_parts.append(f"{actual} < min {lo}")
        if hi is not None and actual > hi:
            ok = False
            reason_parts.append(f"{actual} > max {hi}")
        if not ok:
            any_failed = True
        results.append({
            "key": key,
            "actual": actual,
            "min": lo,
            "max": hi,
            "ok": ok,
            "reason": "; ".join(reason_parts) if reason_parts else None,
            "source": source,
        })

    if not any_evaluated:
        status = "skipped"
    elif any_failed:
        status = "failed"
    else:
        status = "passed"

    return {"status": status, "results": results}
