# Multi-LLM Observatory

Same `radiology_note_summarizer` spec, same fixtures, multiple hosted
backends. The point is spec compliance, not performance ordering.

- `summary.json`: pass rates and mean cost/latency by backend.
- `per_call.json`: one row per backend/fixture call.
- `baseline_full_pass/`: full passing pack.
- `llama_1b_factual_echo_fail/`: schema-clean output that fails factual echo.

Regeneration script lives in local `discussions/` when available.
