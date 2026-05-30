# Replaying Evidence Packs

Every evidence pack contains `replay.sh`. For single-skill packs it reruns the
skill entrypoint and prints JSON; it does not regenerate the whole pack. For
benchmark and LLM-mediated packs, replay calls the relevant eval_engine runner.

## Commands

```bash
bash examples/evidence_packs/<pack>/replay.sh
bash examples/studies/<study>/<pack>/replay.sh

make run-skill SKILL=<skill> \
  FIXTURE=skills/<skill>/fixtures/<fixture> \
  OUT=runs/<new_pack>

make diff RUN_A=examples/evidence_packs/<pack> RUN_B=runs/<new_pack>
```

## Stable files

| File | Purpose |
|---|---|
| `workflow_run_record.md` | human summary |
| `manifest.json` | run identity, command, input or benchmark-manifest hash, file list |
| `validation_summary.json` | gate status and overall verdict |
| `runtime_profile.json` | platform and timing |
| `cost_profile.json` | wall/CPU/RSS/GPU/token observations |
| `agent_run_trace.jsonl` | process and optional LLM trace; v0 records validate against `spec/evidence_pack/agent_run_trace.schema.json` |
| `llm_interaction.json` | LLM-mediated packs only |
| `integrity_check.json` | static integrity findings |
| `environment.lock` | dependency snapshot; committed examples may keep a compact lock and regenerated packs keep the full local `pip freeze` |
| `output.json` | parsed skill output |
| `dataset_run.jsonl` | benchmark packs only |
| `replay.sh` | best-effort replay script |
| `provenance.json` | host GPU/CUDA identity + before/after deltas for declared side-effect paths (full-run packs only) |

Older MVP packs may omit newer files. Treat absence as "gate did not run for
this pack."

## Pack contract and validation

Every pack written by current `eval_engine` runners carries
`pack_format_version` in `manifest.json`. The pack-level contract lives in
[`spec/evidence_pack.schema.json`](../spec/evidence_pack.schema.json) (which
files must exist) and per-file JSON Schemas under
[`spec/evidence_pack/`](../spec/evidence_pack/) (the shape of each JSON file).

```bash
make validate-pack PACK=<dir>
make validate-pack PACK=examples/evidence_packs/dicom_metadata_pass VALIDATE_PACK_ARGS='--allow-legacy'
```

`PACK` may point at a single evidence pack or a trusted-run root containing
`trust_summary.json`; trusted-run validation checks the summary plus the nested
skill and verifier packs it links to.

`--allow-legacy` demotes "missing pack_format_version" to a warning so older
reference packs still validate. New packs should pass without that flag.

## Limits

Replay does not promise bit-identical output, identical dependencies, or
network-stable artifacts. Timestamps, IDs, provider responses, caches, and
upstream downloads can drift. Use `make diff` to separate expected jitter from
spec changes.
