# nat_audit — per-skill token-cost measurement via NeMo Agent Toolkit

This directory measures the **LLM token cost an agent pays to call each
Medical AI Skills skill once**. It wraps every committed skill as a NeMo Agent
Toolkit (NAT) function, runs a fixed tool-calling agent across them, and
records prompt/completion tokens via NAT's profiler.

The skills themselves issue zero LLM tokens (they are training,
benchmarking, and processing pipelines). The measurement here is the
**agent overhead** an LLM-driven caller pays when it decides to invoke
the skill, reads the skill's summary, and emits a final answer.

## Methodology (pinned, do not drift)

| Knob | Value | Reason |
|---|---|---|
| Model | `meta/llama-3.3-70b-instruct` via NVIDIA NIM | Strong enough for reliable tool-call termination at temperature 0; reproducible. |
| Agent type | `tool_calling_agent` | Native function-call schema. `react_agent` hit the 32-call recursion limit during testing. |
| Temperature | `0.0` | Deterministic decisions; comparable across runs. |
| `max_iterations` | `3` | Caps to (1) decide-tool + (1) summarize. Anything more is a wrapper bug, not a real cost. |
| `max_concurrency` | `1` | Serial execution; required for GPU-heavy skills. |
| Profiler | `compute_llm_metrics: true`, `csv_exclude_io_text: true` | Per-LLM-call tokens, no raw I/O text in CSV. |
| Dataset | One question per skill, phrasing names the tool explicitly | Removes tool-selection variance from the measurement. |

Every skill wrapper shells out to the skill's documented entrypoint and
returns a small JSON summary — see `src/nat_audit/register.py`. No skill
internals are reimplemented; we wrap exactly as `SKILL.md` documents.

## Layout

```
tools/nat_audit/
├── README.md                       # this file
├── pyproject.toml                  # nat_audit Python package metadata
├── configs/
│   └── eval_config.yml             # NAT workflow + profiler config
├── data/
│   └── eval.json                   # one question per skill
└── src/
    └── nat_audit/
        ├── __init__.py
        └── register.py             # NAT function wrappers
```

The dedicated venv at `.venv/` is gitignored. `runs/nat_token_audit/`
under the repo root holds the profiler output and is also gitignored.

## Reproducing the measurement

```bash
cd <repo-root>

# 1. Create the venv and install NAT + this package.
uv venv --python 3.12 tools/nat_audit/.venv
source tools/nat_audit/.venv/bin/activate
uv pip install 'nvidia-nat[langchain]' nvidia-nat-profiler
uv pip install -e tools/nat_audit

# 2. Provide an NVIDIA NIM API key (build.nvidia.com free tier).
export NVIDIA_API_KEY="<your nvapi-... key>"

# 3. Run the eval. ~10-15 min wall time depending on GPU/container cache.
rm -rf runs/nat_token_audit
nat eval --config_file tools/nat_audit/configs/eval_config.yml
```

Outputs land in `runs/nat_token_audit/`:

- `standardized_data_all.csv` — every LLM event with `prompt_tokens`,
  `completion_tokens`, `example_number`, `function_name`. Source of
  truth for per-skill token totals.
- `inference_optimization.json` — p90/p95/p99 latency intervals across
  workflow runs.
- `all_requests_profiler_traces.json` — raw trace per LLM call.
- `workflow_output.json` — agent's final answer per dataset item.

## How per-skill totals are computed

Each row in `standardized_data_all.csv` carries an `event_type`. Token
totals live on `LLM_END` rows. `LLM_NEW_TOKEN` rows also carry the
totals (mirrored), so filtering to `LLM_END` once per call is required
to avoid double-counting. Group by `example_number` (0-indexed,
matching dataset order in `data/eval.json`) to slice per skill.

```python
import csv
from collections import defaultdict

per_skill = defaultdict(lambda: {"prompt": 0, "completion": 0, "calls": 0})
for r in csv.DictReader(open("runs/nat_token_audit/standardized_data_all.csv")):
    if r["event_type"] != "LLM_END":
        continue
    n = int(r["example_number"])
    per_skill[n]["prompt"] += int(r["prompt_tokens"] or 0)
    per_skill[n]["completion"] += int(r["completion_tokens"] or 0)
    per_skill[n]["calls"] += 1
```

## Two scenarios measured per skill

The harness measures two different "what does it cost an agent to use
this skill" scenarios, both rooted in the same NAT profiler:

| Scenario | Question phrasing | Tools the agent sees | What it captures |
|---|---|---|---|
| `isolated_tool_call` | "Call the X tool" | only the skill wrappers (9 of them) | Floor: the **irreducible per-tool-call cost** when the agent already knows the skill. Best for **cross-skill comparison**. ~2200-2400 tokens. |
| `end_to_end_workflow` | "I have a CT volume at <path> — first read X's SKILL.md, then call X. Report the result." | skill wrappers + `read_file` + `list_directory` | **Realistic user-driven flow**: agent reads `SKILL.md` (~3000 tokens), maybe inspects the dataset, then invokes the skill, reads the response, summarizes. Closer to what Claude actually pays end-to-end. ~7000-15000 tokens. |

Both numbers are NAT-profiled with the same model/agent. The first is
the lower bound; the second is closer to the real-world cost a
Medical AI Skills user sees through Claude or another agent host. Real
applications typically sit between, closer to `end_to_end_workflow`
when the agent has to discover the skill.

## Where the numbers live in each skill

Every skill's `skill_manifest.yaml` carries a `cost.token_estimate`
block with both scenarios:

```yaml
cost:
  token_estimate:
    common:
      model: meta/llama-3.3-70b-instruct
      agent_type: tool_calling_agent
      measured_at: 2026-05-16
      methodology: tools/nat_audit/README.md
    isolated_tool_call:                  # floor (cross-skill comparison)
      prompt_tokens: 2259
      completion_tokens: 58
      total_tokens: 2317
      llm_calls: 2
      n_tools_in_workflow: 9
    end_to_end_workflow:                 # realistic (user-perspective)
      prompt_tokens: 12345
      completion_tokens: 234
      total_tokens: 12579
      llm_calls: 4
      n_tools_in_workflow: 11            # +read_file +list_directory
      scenario: |
        "I have a CT volume. Read SKILL.md, then call the skill."
```

This is **agent-overhead** cost, not the skill's compute cost. Compute
cost remains in `runs/<eval>/cost_profile.json` (wall, CPU, GPU seconds,
peak RAM).

## What this does NOT measure

- **System prompts a different host supplies.** NAT's default tool-calling-agent
  system prompt is fixed and short. Claude Code, Cursor, etc. have their
  own (longer) system prompts that shift the numbers up.
- **Conversation history across multiple turns.** Each scenario measures
  one user question. Real chat sessions carry prior turns forward, which
  is mostly cacheable with Anthropic prompt caching but not captured here.
- **Prompt caching.** All numbers assume cold context. Anthropic prompt
  caching applied at the workflow level brings repeated content (SKILL.md
  reads, tool descriptions) to ~10% of the listed cost on subsequent turns.

If your real workflow uses a different model, agent type, prompt shape,
or chains many skills, re-run with those values — the per-skill number
is not portable across configurations.
