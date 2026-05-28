# nv-generate-vae-finetune Benchmark

This benchmark report covers `nv-generate-vae-finetune`, the Medical AI
Skills wrapper for NV-Generate-CTMR VAE finetuning.

| Arm | Context | Expected behavior | Status |
|---|---|---|---|
| With skill | `SKILL.md` plus wrapper script | Agent validates the datalist, stages VAE configs, and runs the skill-owned VAE runner against existing upstream helpers. | Preflight implemented. |
| Without skill | User prompt plus upstream notebook | Agent may paste notebook cells, skip validation data setup, or save checkpoints outside the requested output directory. | Baseline run pending. |

Full GPU evidence is intentionally not bundled because it requires user
training volumes, CUDA, and model weights. The committed fixture is
preflight-only and verifies datalist shape, upstream discovery, config staging,
and manifest gates without committing NIfTI data.
