import json
import subprocess
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval_engine.run_benchmark import _dice_iou, _hausdorff  # noqa: E402


def _write_nifti(path, arr):
    nib.save(nib.Nifti1Image(arr.astype(np.uint8), np.eye(4)), str(path))


def test_segmentation_metrics_perfect_overlap(tmp_path):
    arr = np.zeros((6, 6, 6), dtype=np.uint8)
    arr[2:4, 2:4, 2:4] = 1
    dice, iou = _dice_iou(arr > 0, arr > 0)
    assert dice == 1.0
    assert iou == 1.0
    assert _hausdorff(arr > 0, arr > 0, (1.0, 1.0, 1.0)) == 0.0


def test_run_benchmark_end_to_end(tmp_path):
    skill = tmp_path / "copy_skill"
    scripts = skill / "scripts"
    scripts.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Copy Skill\n")
    (skill / "skill_manifest.yaml").write_text(
        "\n".join(
            [
                "id: test.copy_seg",
                "version: 0.1.0",
                "inputs:",
                "  - name: volume",
                "    type: file_path",
                "    formats: [nifti]",
                "outputs:",
                "  - name: mask",
                "    type: file_path",
                "    formats: [nifti]",
                "  - name: result_json",
                "    type: json",
                "runtime:",
                "  language: python",
                "  entrypoint: scripts/copy_seg.py",
            ]
        )
    )
    (scripts / "copy_seg.py").write_text(
        "import json, sys\n"
        "p = sys.argv[1]\n"
        "print(json.dumps({'skill': 'copy_seg', 'output': {'path': p}}))\n"
    )

    data = tmp_path / "data"
    data.mkdir()
    mask = np.zeros((5, 5, 5), dtype=np.uint8)
    mask[1:4, 1:4, 1:4] = 1
    input_path = data / "case001.nii.gz"
    gt_path = data / "case001_gt.nii.gz"
    _write_nifti(input_path, mask)
    _write_nifti(gt_path, mask)

    benchmark = tmp_path / "dataset.benchmark.yaml"
    benchmark.write_text(
        "\n".join(
            [
                "format: benchmark_dataset",
                "source: synthetic",
                "dataset: synthetic_copy_seg",
                "case_count: 1",
                "prediction:",
                "  path: output.path",
                "sanity_checks:",
                "  - {path: output.dice.mean, gte: 1.0}",
                "  - {path: output.fail_count, eq: 0}",
                "  - {path: output.coverage_pct, gte: 100}",
                "cases:",
                "  - id: case001",
                f"    input: {input_path}",
                f"    ground_truth: {gt_path}",
                "    label: 1",
            ]
        )
    )

    out = tmp_path / "benchmark_pack"
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "eval_engine" / "run_benchmark.py"),
            str(skill),
            "--benchmark",
            str(benchmark),
            "--out",
            str(out),
            "--jobs",
            "2",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    summary = json.loads((out / "output.json").read_text())
    validation = json.loads((out / "validation_summary.json").read_text())
    records = (out / "dataset_run.jsonl").read_text().strip().splitlines()
    assert summary["output"]["dice"]["mean"] == 1.0
    assert summary["output"]["iou"]["mean"] == 1.0
    assert summary["output"]["hd"]["mean"] == 0.0
    assert validation["overall_status"] == "passed"
    assert len(records) == 1
