from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import jsonschema

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPT = SKILL / "scripts" / "run_flow_benchmark.py"
FIXTURE = SKILL / "fixtures" / "default"
SCHEMA = SKILL / "validators" / "output_schema.json"
CONTRACT = SKILL / "contracts" / "endoscopy_tool_tracking.yaml"


def _make_stub_holohub_root(tmp_path: Path) -> Path:
    root = tmp_path / "holohub"
    bench = root / "benchmarks" / "holoscan_flow_benchmarking"
    bench.mkdir(parents=True)
    data = root / "data" / "endoscopy"
    data.mkdir(parents=True)
    (data / "tool_loc_convlstm.onnx").write_bytes(b"stub-onnx" * 64)
    (data / "surgical_video.gxf_entities").write_bytes(b"stub-entities" * 64)
    (data / "surgical_video.gxf_index").write_bytes(b"stub-index" * 64)
    app_source = root / "applications" / "endoscopy_tool_tracking" / "python"
    app_source.mkdir(parents=True)
    (app_source / "endoscopy_tool_tracking.py").write_text("# stub endoscopy app\n")

    holohub = root / "holohub"
    holohub.write_text(
        "#!/usr/bin/env bash\n"
        "if [[ \"$1\" == \"run-container\" ]]; then\n"
        "  shift\n"
        "  CMD=\"\"\n"
        "  while [[ $# -gt 0 ]]; do\n"
        "    if [[ \"$1\" == \"--\" ]]; then\n"
        "      shift\n"
        "      CMD=\"$*\"\n"
        "      break\n"
        "    fi\n"
        "    shift\n"
        "  done\n"
        "  CMD=\"${CMD//\\/workspace\\/holohub/$PWD}\"\n"
        "  bash -c \"$CMD\"\n"
        "  exit $?\n"
        "fi\n"
        "if [[ \"$1\" == \"build\" ]]; then\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n"
    )
    holohub.chmod(0o755)

    benchmark = bench / "benchmark.py"
    benchmark.write_text(
        "#!/usr/bin/env python3\n"
        "import argparse\n"
        "from pathlib import Path\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('-a', '--holohub-application', default='endoscopy_tool_tracking')\n"
        "p.add_argument('--language', default='python')\n"
        "p.add_argument('-d', '--log-directory', required=True)\n"
        "p.add_argument('--sched', nargs='+', required=True)\n"
        "p.add_argument('-r', '--runs', type=int, default=1)\n"
        "p.add_argument('-i', '--instances', type=int, default=1)\n"
        "p.add_argument('-m', '--num_messages', type=int, default=100)\n"
        "p.add_argument('-w', '--num_worker_threads', type=int, default=1)\n"
        "p.add_argument('-u', '--monitor_gpu', action='store_true')\n"
        "p.add_argument('-g', '--gpu', default='all')\n"
        "p.add_argument('--run-command', default='')\n"
        "args = p.parse_args()\n"
        "out = Path(args.log_directory)\n"
        "out.mkdir(parents=True, exist_ok=True)\n"
        "for sched in args.sched:\n"
        "  for run in range(1, args.runs + 1):\n"
        "    for inst in range(1, args.instances + 1):\n"
        "      log = out / f'logger_{sched}_{run}_{inst}.log'\n"
        "      with log.open('w') as f:\n"
        "        for n in range(args.num_messages):\n"
        "          base = 10**9 + n * 10**5\n"
        "          f.write(\n"
        "            f'(Endoscopy App.replayer,{base},{base + 1000}) -> '\n"
        "            f'(Endoscopy App.format_converter,{base + 1500},{base + 2500}) -> '\n"
        "            f'(Endoscopy App.lstm_inferer,{base + 3000},{base + 8000}) -> '\n"
        "            f'(Endoscopy App.tool_tracking_postprocessor,{base + 8500},{base + 8800}) -> '\n"
        "            f'(Endoscopy App.holoviz,{base + 9000},{base + 12000})\\n'\n"
        "          )\n"
        "          f.write(\n"
        "            f'(Endoscopy App.replayer,{base},{base + 1000}) -> '\n"
        "            f'(Endoscopy App.holoviz,{base + 9000},{base + 12000})\\n'\n"
        "          )\n"
        "    if args.monitor_gpu:\n"
        "      (out / f'gpu_utilization_{sched}_{run}.csv').write_text('20,30,40,\\n')\n"
        "(out / 'benchmark.log').write_text('Evaluation completed for endoscopy_tool_tracking.\\n')\n"
        "print('stub benchmark complete')\n"
    )
    benchmark.chmod(0o755)

    git = [
        "git",
        "-C",
        str(root),
        "-c",
        "user.email=test@example.com",
        "-c",
        "user.name=Test",
        "-c",
        "commit.gpgsign=false",
    ]
    subprocess.run(git + ["init", "-q"], check=True)
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + ["commit", "-q", "-m", "stub"], check=True)
    return root


def test_generic_contract_assertions_pass(tmp_path: Path) -> None:
    root = _make_stub_holohub_root(tmp_path)
    env = os.environ.copy()
    env.update(
        {
            "HOLOHUB_ROOT": str(root),
            "HOLOHUB_BENCHMARK_APP": "endoscopy_tool_tracking",
            "HOLOHUB_BENCHMARK_CONTRACT": str(CONTRACT),
            "HOLOHUB_BENCHMARK_BUILD": "false",
            "HOLOHUB_BENCHMARK_MONITOR_GPU": "true",
            "HOLOHUB_BENCHMARK_MESSAGES": "100",
        }
    )
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURE)],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    jsonschema.validate(payload, json.loads(SCHEMA.read_text()))
    assert payload["skill"] == "holohub_flow_benchmark"
    assert payload["contract"]["present"] is True
    assert payload["contract"]["assertions"]["all_required_assertions_passed"] is True
    assert payload["domain"]["scheduler_coverage_complete"] is True
