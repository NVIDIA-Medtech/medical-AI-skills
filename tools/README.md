# tools/

Maintainer utilities, profilers, and experiments for Medical AI Skills. **Not** part
of the skill runtime contract.

End users and agents adopt skills from `skills/` via each skill's `SKILL.md`
and `scripts/`. Nothing under `tools/` is required to run a published skill unless
that dependency is explicitly documented in the skill itself.

## Layout

| Path | Purpose |
|---|---|
| [`nat_audit/`](nat_audit/) | Measure LLM token cost when an agent invokes Medical AI Skills skills via NeMo Agent Toolkit |
| [`contract_summary/`](contract_summary/) | Render read-only contract summaries from `SKILL.md` and `skill_manifest.yaml` before a run |
| [`review_packet/`](review_packet/) | Render compact Markdown review packets from existing evidence packs and trusted-run directories |
| [`trace_inventory/`](trace_inventory/) | Inventory `agent_run_trace.jsonl` field shapes before formal trace-schema work |

Add new tools as `tools/<name>/` with a local `README.md` and reproducible
commands. Prefer a dedicated venv when dependencies conflict with repo v0
policy (for example NAT under `nat_audit/`).

## Relationship to eval_engine

| Layer | Role |
|---|---|
| `eval_engine/run.py` | source of truth for skill correctness and evidence packs |
| `eval_engine/run_llm_skill.py` | minimal LLM dispatch smoke test (one approved tool call → nested pack) |
| `tools/nat_audit/` | richer agent workflow profiler (token cost, multi-tool overhead) |

NAT is a candidate **agent-backend adapter**, not a replacement for the harness.
A future promotion path is: NAT workflows call `eval_engine/run.py` (or emit
nested packs with the same file names) so agent-use measurements stay comparable
to other evidence. Do not make skills depend on NAT at runtime.

## Graduation

Promote logic out of `tools/` only when it becomes generic shared infrastructure:

- **eval_engine/** — generic gates, runners, or pack writers used by all specs
- **spec/** — contract changes that affect manifests or evidence packs
- **docs/** — stable user or contributor documentation

Do not move one-off experiments into `eval_engine/` without tests and a clear
manifest or replay contract.

## Contributing

See [`CONTRIBUTING.md`](../CONTRIBUTING.md#tools-policy) for the tools
contribution lane.
