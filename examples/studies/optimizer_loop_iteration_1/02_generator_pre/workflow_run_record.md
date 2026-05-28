# Workflow Run Record

- run id: 436323f8c254
- skill: radiology_note_summarizer v0.1.0
- started: 2026-05-09T22:11:34.091614+00:00
- finished: 2026-05-09T22:11:36.947410+00:00
- elapsed: 2.856s
- exit code: 0

## Skill
- dir: skills/radiology-note-summarizer
- entrypoint: scripts/summarize.py

## Fixture
- path: skills/radiology-note-summarizer/fixtures/case_001_input.json
- sha256: 3865a75b981fba0f5bcc4154def492bd6d590d36a1ada8e8e2e02eb09d9ee2f3
- size: 537 bytes

## Validation
- overall: failed (sanity/runtime/integrity/cost/factual_echo/model_identity gate)
- schema: passed
- sanity: failed
- runtime: within_envelope
- cost: passed
- integrity: clean

## Output (excerpt)
```json
{
  "output": {
    "study_instance_uid": "1.2.826.0.1.3680043.8.498.79927183420192038472634851012345",
    "findings": [
      "mild hepatic steatosis",
      "small simple cyst in the right kidney (1.5 cm)"
    ],
    "impressions": "Mild hepatic steatosis and incidental 1.5 cm simple cyst in the right kidney.",
    "flags_for_followup": [
      "symptoms persist"
    ]
  },
  "runtime": {
    "model": "nvidia/mistralai/mistral-7b-instruct-v0.3",
    "requested_model": "nvidia/mistralai/mistral-7b-instruct-v0.3",
    "system_fingerprint": null,
    "endpoint": "https://inference-api.nvidia.com/v1",
    "temperature": 0.0,
    "max_tokens": 1024,
    "seed": 42,
    "request_id": "chatcmpl-c7d6d36667b1439aa2c33833bc4f6a0e",
    "prompt_template_sha256": "b745fefb9a043f9527efdc5ef4854735053294d28bf9c2dec0e5a9b7c5b38a33",
    "system_prompt_sha256": "b8f23d832d5e79d130a8f0cb49b0a50e61751a98904dd411e3678f31094a8889",
    "llm_tokens_input": 618,
    "llm_tokens_output": 156,
    "elapsed_seconds": 2.7553
  }
}
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.