# Workflow Run Record

- run id: 0ab8480bb636
- skill: radiology_note_summarizer v0.1.0
- started: 2026-05-09T22:10:06.818169+00:00
- finished: 2026-05-09T22:10:08.994611+00:00
- elapsed: 2.176s
- exit code: 0

## Skill
- dir: skills/radiology-note-summarizer
- entrypoint: scripts/summarize.py

## Fixture
- path: skills/radiology-note-summarizer/fixtures/case_001_input.json
- sha256: 3865a75b981fba0f5bcc4154def492bd6d590d36a1ada8e8e2e02eb09d9ee2f3
- size: 537 bytes

## Validation
- overall: passed
- schema: passed
- sanity: passed
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
      "small simple cyst in right kidney measuring ~1.5 cm, likely incidental",
      "no acute findings"
    ],
    "impressions": "CT abdomen with contrast shows mild hepatic steatosis and an incidental 1.5 cm simple cyst in the right kidney; no acute abdominal pathology.",
    "flags_for_followup": [
      "Follow up if symptoms persist"
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
    "request_id": "chatcmpl-8a1f11a866a4dc22",
    "prompt_template_sha256": "b745fefb9a043f9527efdc5ef4854735053294d28bf9c2dec0e5a9b7c5b38a33",
    "system_prompt_sha256": "b8f23d832d5e79d130a8f0cb49b0a50e61751a98904dd411e3678f31094a8889",
    "llm_tokens_input": 552,
    "llm_tokens_output": 292,
    "elapsed_seconds": 2.0877
  }
}
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.