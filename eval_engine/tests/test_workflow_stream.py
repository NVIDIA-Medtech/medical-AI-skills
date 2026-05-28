"""Workflow stream block aggregates holoscan flow benchmark step output."""
from eval_engine.workflow_stream import (
    STREAM_FORMAT_VERSION,
    build_workflow_stream_block,
    extract_flow_benchmark_stream,
)


def _flow_payload() -> dict:
    return {
        "skill": "holohub_flow_benchmark",
        "plan": {
            "app": "imaging_ai_segmentator",
            "language": "python",
            "schedulers": ["greedy", "multithread"],
            "messages": 5,
            "mode": "smoke",
            "smoke_mode": True,
            "run_mode": "container",
        },
        "invocation": {
            "holohub_commit": "abc123",
            "benchmark_exit_code": 0,
            "container_exit_code": 0,
            "output_dir": "/tmp/flow_out",
        },
        "output": {
            "logger": {
                "count": 2,
                "total_bytes": 4096,
                "files": [{"path": "logger_greedy_1_1.log", "bytes": 2048, "sha256": "x"}],
            },
            "gpu_utilization": {"count": 0, "total_bytes": 0, "files": []},
            "other": {"count": 0, "total_bytes": 0, "files": []},
        },
        "analysis": {
            "paths_observed": 2,
            "total_latency_samples": 160,
            "skip_begin_messages": 0,
            "discard_last_messages": 0,
            "first_path": {
                "scheduler": "greedy",
                "path": "App.replayer -> App.infer",
                "p95_ms": 12.5,
                "p99_ms": 14.0,
                "sample_count": 80,
            },
            "schedulers": {
                "greedy": {
                    "path_count": 1,
                    "paths": {
                        "App.replayer -> App.infer": {
                            "p95_ms": 12.5,
                            "p99_ms": 14.0,
                            "sample_count": 80,
                            "avg_ms": 10.0,
                        }
                    },
                },
                "multithread": {
                    "path_count": 1,
                    "paths": {
                        "App.replayer -> App.infer": {
                            "p95_ms": 11.0,
                            "sample_count": 80,
                        }
                    },
                },
            },
            "gpu_utilization": {
                "sample_count": 0,
                "avg_percent": None,
                "max_percent": None,
            },
        },
        "domain": {
            "scheduler_coverage_complete": True,
            "logger_count_matches_plan": True,
            "benchmark_log": {"present": True, "bytes": 100},
        },
        "contract": {
            "present": True,
            "path": "contracts/imaging.yaml",
            "smoke_mode": True,
            "assertions": {
                "all_required_assertions_passed": True,
                "scheduler_coverage_complete": True,
                "latency_budgets_met": True,
            },
            "latency_budget_results": {
                "greedy": {"p95_ms_max": True},
            },
            "scheduler_results": {
                "greedy": {
                    "primary_path": "App.replayer -> App.infer",
                    "p95_ms": 12.5,
                    "sample_count": 80,
                }
            },
        },
    }


def test_extract_flow_benchmark_stream_shape() -> None:
    entry = extract_flow_benchmark_stream(
        "flow_benchmark",
        _flow_payload(),
        step_record={"skill": "skills/holohub-flow-benchmark", "overall_status": "passed"},
    )
    holoscan = entry["holoscan_flow"]
    assert entry["holohub_app"] == "imaging_ai_segmentator"
    assert holoscan["plan"]["mode"] == "smoke"
    assert holoscan["artifacts"]["logger"]["count"] == 2
    assert holoscan["latency"]["by_scheduler"]["greedy"]["paths"][0]["p95_ms"] == 12.5
    assert holoscan["contract"]["all_assertions_passed"] is True


def test_build_workflow_stream_block_rollup() -> None:
    context = {
        "holohub_app": {"output": {"dicom_seg": {"count": 1}}},
        "flow_benchmark": _flow_payload(),
    }
    step_results = [
        {"id": "holohub_app", "skill": "skills/holohub-imaging-ai-segmentator", "overall_status": "passed"},
        {"id": "flow_benchmark", "skill": "skills/holohub-flow-benchmark", "overall_status": "passed"},
    ]
    block = build_workflow_stream_block(context, step_results)
    assert block["stream_format_version"] == STREAM_FORMAT_VERSION
    assert block["present"] is True
    assert block["holohub_app"] == "imaging_ai_segmentator"
    assert block["holohub_commit"] == "abc123"
    assert block["primary_latency"]["p95_ms"] == 12.5
    assert "flow_benchmark" in block["steps"]
    assert "holohub_app" not in block["steps"]
