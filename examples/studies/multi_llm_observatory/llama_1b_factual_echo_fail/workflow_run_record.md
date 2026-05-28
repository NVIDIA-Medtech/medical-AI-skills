# Workflow Run Record

- run id: ac79c9c93053
- skill: radiology_note_summarizer v0.1.0
- started: 2026-05-09T22:11:31.032794+00:00
- finished: 2026-05-09T22:11:32.181317+00:00
- elapsed: 1.148s
- exit code: 0

## Skill
- dir: skills/radiology-note-summarizer
- entrypoint: scripts/summarize.py

## Fixture
- path: skills/radiology-note-summarizer/fixtures/case_004_terse.json
- sha256: fea666164be61510374dda2e6e7061fad05832f8b3b58e93efe7ac3590ba4e15
- size: 309 bytes

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
    "study_instance_uid": "2.16.840.1.113669.632.20.121711.10000158860",
    "findings": [],
    "impressions": "No acute findings.",
    "flags_for_followup": []
  },
  "runtime": {
    "model": "nvidia/meta/llama-3.2-1b-instruct",
    "requested_model": "nvidia/meta/llama-3.2-1b-instruct",
    "system_fingerprint": null,
    "endpoint": "https://inference-api.nvidia.com/v1",
    "temperature": 0.0,
    "max_tokens": 1024,
    "seed": 42,
    "request_id": "chatcmpl-e84664e0e98e48b1bc9d510c0407e725",
    "prompt_template_sha256": "b745fefb9a043f9527efdc5ef4854735053294d28bf9c2dec0e5a9b7c5b38a33",
    "system_prompt_sha256": "9420615cdcaa060fdff0af906a08828f151ff9583c9e9a5ce5c4fa1054095e04",
    "llm_tokens_input": 504,
    "llm_tokens_output": 60,
    "elapsed_seconds": 1.0766
  }
}
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.