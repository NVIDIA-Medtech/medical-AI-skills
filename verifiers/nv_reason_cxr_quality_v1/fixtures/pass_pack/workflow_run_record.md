# Workflow Run Record

- run id: 2b4ea200a2ac
- skill: medagent.nv_reason_cxr v0.1.0
- started: 2026-05-26T02:10:27.744137+00:00
- finished: 2026-05-26T02:10:27.860718+00:00
- elapsed: 0.117s
- exit code: 0

## Skill
- dir: skills/nv-reason-cxr
- entrypoint: scripts/run_nv_reason_cxr.py

## Fixture
- path: skills/nv-reason-cxr/fixtures/synthetic_cxr_input.json
- sha256: 7cb121e969161d99c932b4b99159d88b3c4394743d016cdd966ebd54078a8b15
- size: 387 bytes

## Validation
- overall: passed
- schema: passed
- sanity: passed
- runtime: within_envelope
- cost: passed
- env_pin: skipped
- integrity: clean

## Output (excerpt)
```json
{
  "input": {
    "case_id": "synthetic-cxr-smoke",
    "image": {
      "format": "png",
      "height": 96,
      "path": "<repo>/verifiers/nv_reason_cxr_quality_v1/fixtures/pass_pack/artifacts/input_synthetic_chest_xray.png",
      "sha256": "767c7ad1c4e799c0b177015970ef7dafa7feedcfad11e03c992146cffb6569cf",
      "source": "generated_fixture",
      "width": 96
    },
    "prompt": "Find abnormalities and support devices."
  },
  "limitations": [
    "Output is engineering evidence only; it is not a diagnosis or treatment recommendation.",
    "NV-Reason-CXR-3B can hallucinate, miss findings, or produce overconfident prose.",
    "A qualified professional must review any medical workflow use."
  ],
  "output": {
    "response_text": "Mock NV-Reason-CXR response for a generated synthetic chest X-ray image. No clinical finding is asserted; this response only verifies image handling, prompt wiring, JSON output, and evidence-pack gates.",
    "text_chars": 202
  },
  "runtime": {
    "device": "none",
    "generated_tokens": 0,
    "inference_seconds": 1e-06,
    "local_files_only": false,
    "max_new_tokens": 2048,
    "mock": true,
    "mode": "mock",
    "model": "nvidia/NV-Reason-CXR-3B",
    "torch_dtype": "none",
    "torch_version": null,
    "transformers_version": null,
    "truncated_by_max_new_tokens": false
  },
  "skill": "nv_reason_cxr"
}
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.
