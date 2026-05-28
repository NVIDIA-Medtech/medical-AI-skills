# Workflow Run Record

- run id: 17dcfa00775e
- skill: radiology_note_summarizer v0.1.0
- started: 2026-05-26T01:59:45.742662+00:00
- finished: 2026-05-26T01:59:45.859585+00:00
- elapsed: 0.117s
- exit code: 0

## Skill
- dir: skills/radiology-note-summarizer
- entrypoint: scripts/summarize.py

## Fixture
- path: skills/radiology-note-summarizer/fixtures/case_001_input.json
- sha256: 1ff89777f2a0e16612708f121ed81e829a0405574eda1bac8ae900ee8c156653
- size: 494 bytes

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
  "output": {
    "study_instance_uid": "SYNTH-STUDY-001",
    "findings": [
      "CT of the abdomen performed with contrast",
      "mild hepatic steatosis noted",
      "small simple right renal cyst, approximately 1.5 cm, likely incidental",
      "no acute findings"
    ],
    "impressions": "CT abdomen: mild hepatic steatosis and a small incidental right renal cyst. No acute process.",
    "flags_for_followup": [
      "clinical follow-up if symptoms persist"
    ]
  },
  "runtime": {
    "model": "nvidia/openai/gpt-oss-20b",
    "requested_model": "nvidia/openai/gpt-oss-20b",
    "system_fingerprint": null,
    "endpoint": "https://inference-api.nvidia.com/v1",
    "temperature": 0.0,
    "max_tokens": 1024,
    "seed": 42,
    "request_id": "mock-b55fe9c4e907",
    "prompt_template_sha256": "b745fefb9a043f9527efdc5ef4854735053294d28bf9c2dec0e5a9b7c5b38a33",
    "system_prompt_sha256": "177d8be9ff3f33ecde154b548bbe4a7e7a4bfa5b29fdd7aa8a49895c2ffa70fb",
    "llm_tokens_input": 331,
    "llm_tokens_output": 101,
    "elapsed_seconds": 0.0006,
    "mock": true
  }
}
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.