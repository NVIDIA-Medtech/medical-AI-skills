# Workflow Run Record

- run id: d5b07f6884d9
- skill: radiology_note_summarizer v0.1.0
- started: 2026-05-09T22:11:38.473689+00:00
- finished: 2026-05-09T22:11:41.218444+00:00
- elapsed: 2.745s
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
      "CT",
      "ABDOMEN"
    ],
    "impressions": "Mild hepatic steatosis and a 1.5 cm simple cyst in the right kidney, likely incidental. No acute findings.",
    "flags_for_followup": [
      "if symptoms persist"
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
    "request_id": "chatcmpl-5f579ad567834e66af13e112b7a50f44",
    "prompt_template_sha256": "b745fefb9a043f9527efdc5ef4854735053294d28bf9c2dec0e5a9b7c5b38a33",
    "system_prompt_sha256": "cd9b0adec341398ec6ea2d5c2552491bb50acf1bfbbabe4e8dcd9a48d65fc092",
    "llm_tokens_input": 642,
    "llm_tokens_output": 144,
    "elapsed_seconds": 2.6179
  }
}
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.