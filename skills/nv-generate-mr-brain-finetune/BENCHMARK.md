# nv-generate-mr-brain-finetune Benchmark

This benchmark report covers `nv-generate-mr-brain-finetune`, the Medical AI
Skills wrapper for NV-Generate-CTMR MR-brain diffusion-UNet finetuning.

| Arm | Context | Expected behavior | Status |
|---|---|---|---|
| With skill | `SKILL.md` plus wrapper script | Agent validates the datalist and orchestrates the existing upstream training scripts. | Preflight implemented. |
| Without skill | User prompt plus upstream notebook | Agent may paste notebook cells, skip embedding sidecar JSON creation, or run training before staging configs. | Baseline run pending. |

Full GPU evidence is intentionally not bundled because it requires user
training volumes, CUDA, and model weights. The committed fixture is
preflight-only and verifies command shape, upstream discovery, and manifest
gates without committing NIfTI data.
