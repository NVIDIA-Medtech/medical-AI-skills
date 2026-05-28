# Workflow Run Record

- run id: f5160921bf6b
- skill: medagent.nv_segment_ct_finetune v0.4.1
- started: 2026-05-26T04:17:46.329512+00:00
- finished: 2026-05-26T04:18:26.842252+00:00
- elapsed: 40.513s
- exit code: 0

## Skill
- dir: skills/nv-segment-ct-finetune
- entrypoint: scripts/run_finetune.py

## Fixture
- path: skills/nv-segment-ct-finetune/fixtures/spleen_micro
- sha256: 20018681fcd2aa9831af042da4574777c109b135af9664da27cb94d382355c49
- size: 12761707 bytes

## Validation
- overall: passed
- schema: passed
- sanity: passed
- runtime: within_envelope
- cost: passed
- env_pin: passed
- integrity: clean

## Output (excerpt)
```json
{
  "skill": "nv_segment_ct_finetune",
  "model": "NVIDIA-Medtech/NV-Segment-CT (VISTA3D)",
  "model_repo": "https://huggingface.co/nvidia/NV-Segment-CT",
  "version": "0.4.1",
  "input": {
    "dataset_dir": "<repo>/skills/nv-segment-ct-finetune/fixtures/spleen_micro",
    "datalist": "<repo>/skills/nv-segment-ct-finetune/fixtures/spleen_micro/datalist.json",
    "n_train_cases": 4,
    "label_mappings": {
      "default": [
        [
          1,
          3
        ]
      ]
    },
    "label_mapping_resolution": {
      "source": "anatomy_lookup",
      "anatomy": "spleen",
      "user_idx": 1,
      "vista3d_idx": 3
    },
    "dataset_audit": {
      "dataset_dir": "<repo>/skills/nv-segment-ct-finetune/fixtures/spleen_micro",
      "datalist_source": "caller_provided",
      "datalist_path": "<repo>/skills/nv-segment-ct-finetune/fixtures/spleen_micro/datalist.json",
      "n_pairs": 4
    },
    "smoke": true,
    "sanity": false,
    "auto_seg": false,
    "formal_eval": false
  },
  "environment": {
    "gpu_count": 1,
    "gpu_name": "NVIDIA RTX 6000 Ada Generation",
    "gpu_total_mb": 49140,
    "gpu_free_mb": 48342,
    "host_ram_mb": 61915,
    "cuda_available": true,
    "python": "3.12.3",
    "packages": {
      "monai": "1.4.0",
      "torch": "2.12.0",
      "nibabel": "5.4.2",
      "scipy": "1.16.0",
      "typer": "0.25.1",

```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.
