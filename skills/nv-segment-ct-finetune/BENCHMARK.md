# Skill Benchmark: nv-segment-ct-finetune

> ❌ **Overall verdict: FAIL — Publication blocked**

The skill should be reviewed before publication. Address the blocking findings below, then rerun Skill Evaluator.

## Evaluation Metadata

- Skill: `nv-segment-ct-finetune`
- Evaluation date: 2026-09-14
- Evaluator version: `1.5.6`
- Agents: Claude Code (`aws/anthropic/bedrock-claude-opus-4-8`), Codex (`openai/openai/gpt-5.5`)
- Tasks: 4 evaluation tasks (4 positive)
- Dataset digest: `sha256:d41af257bcccc6bfdc4eeff8f516d55c89024acd4b8ebe5452e2c34717040a83` (skill-evaluator-dataset-snapshot/1)
- Attempts per task: 3
- Environment: `k8s-sandbox`
- Tier 2 evidence: required for publication
- Tier 3 evidence: required for publication

Each task attempt ran in its own isolated sandbox pod.

## What This Report Answers

The three-tier evaluation checks whether the skill:

- is safe to use;
- produces correct answers;
- is discovered and activated when needed;
- helps the agent complete the user's goal and expected workflow; and
- avoids wasted skill and tool usage.

## Results at a Glance

| Measure | Claude Code (Baseline → Skill Uplift) | Codex (Baseline → Skill Uplift) |
|---|---:|---:|
| Overall | 93.9% — baseline ran, but no comparable score was available; uplift unavailable | 95.3% — baseline ran, but no comparable score was available; uplift unavailable |
| Security | 92.9% → 100.0% (+7.1 points) | 100.0% → 100.0% (±0.0 points) |
| Correctness | 48.6% → 95.0% (+46.4 points) | 95.0% → 95.0% (±0.0 points) |
| Discoverability | 100.0% — baseline ran, but no comparable score was available; uplift unavailable | 93.8% — baseline ran, but no comparable score was available; uplift unavailable |
| Effectiveness | 28.2% → 88.3% (+60.1 points) | 81.7% → 90.4% (+8.7 points) |
| Efficiency | 86.0% — baseline ran, but no comparable score was available; uplift unavailable | 97.5% — baseline ran, but no comparable score was available; uplift unavailable |

**How to read this table:** baseline is the same task attempted without the target skill. Scores are rounded to one decimal; threshold-adjacent values use additional precision so their displayed band matches the verdict. Uplift is derived from those displayed scores and shown in percentage points.

Example: `47.0% → 92.0% (+45.0 points)` means the skill-assisted run scored 92.0%, 45.0 percentage points above its 47.0% no-skill baseline.

## Token Usage

Actual Tier 3 execution usage is reported for every observed agent/case pair and both conditions.

| Agent | Dataset case | With skill | Without skill | Delta | Change | Coverage |
|---|---|---:|---:|---:|---:|---|
| claude-code | All cases | 942,910 | 2,756,316 | N/A | N/A | skill 4/4; base 7/7 |
| claude-code | fixed-channel-softmax-finetune | 416,575 | 626,626 | N/A | N/A | skill 1/1; base 2/2 |
| claude-code | local-mlflow-tracking | 69,239 | 131,469 | -62,230 | -47.33% | skill 1/1; base 1/1 |
| claude-code | reject-new-class-invention | 388,894 | 1,609,892 | -1,220,998 | -75.84% | skill 1/1; base 1/1 |
| claude-code | smoke-test-before-training | 68,202 | 388,329 | N/A | N/A | skill 1/1; base 3/3 |
| codex | All cases | 246,300 | 460,148 | -213,848 | -46.47% | skill 4/4; base 4/4 |
| codex | fixed-channel-softmax-finetune | 31,025 | 67,511 | -36,486 | -54.04% | skill 1/1; base 1/1 |
| codex | local-mlflow-tracking | 30,871 | 53,948 | -23,077 | -42.78% | skill 1/1; base 1/1 |
| codex | reject-new-class-invention | 135,882 | 243,719 | -107,837 | -44.25% | skill 1/1; base 1/1 |
| codex | smoke-test-before-training | 48,522 | 94,970 | -46,448 | -48.91% | skill 1/1; base 1/1 |
| ALL AGENTS | Dataset aggregate | 1,189,210 | 3,216,464 | N/A | N/A | skill 8/8; base 11/11 |

Prompt tokens include cached reads, so total tokens are `prompt + completion` (cached is not added twice). The Efficiency score uses `(prompt - cached) + completion`. N/A means the relevant trajectory counters were not available; coverage is never estimated.

## Tier Status

| Tier | Purpose | Status | Evidence |
|---|---|---|---|
| Tier 1 | Static validation | **FAILED** | 11 validator(s); 28 finding(s) |
| Tier 2 | Semantic deduplication | **PASSED** | 2 validator(s); 0 finding(s) |
| Tier 3 | Live agent evaluation | **PASS** | 2 agent(s); 4 task(s) |

## Blocking Findings

- **MEDIUM** BANDIT/B310:blacklist: Audit url open for permitted schemes. Allowing use of file:/ or custom schemes is often unexpected. (CWE-22) (`skills/nv-segment-ct-finetune/scripts/run_finetune.py:453`)
- **MEDIUM** BANDIT/B614:pytorch_load: Use of unsafe PyTorch load (CWE-502) (`skills/nv-segment-ct-finetune/scripts/run_finetune.py:1390`)
- **MEDIUM** BANDIT/B614:pytorch_load: Use of unsafe PyTorch load (CWE-502) (`skills/nv-segment-ct-finetune/scripts/run_finetune.py:1391`)

## Findings and Observations

<details>
<summary>Show detailed findings and successful checks</summary>

- **MEDIUM** BANDIT/B310:blacklist: Audit url open for permitted schemes. Allowing use of file:/ or custom schemes is often unexpected. (CWE-22) (`skills/nv-segment-ct-finetune/scripts/run_finetune.py:453`)
- **MEDIUM** BANDIT/B614:pytorch_load: Use of unsafe PyTorch load (CWE-502) (`skills/nv-segment-ct-finetune/scripts/run_finetune.py:1390`)
- **MEDIUM** BANDIT/B614:pytorch_load: Use of unsafe PyTorch load (CWE-502) (`skills/nv-segment-ct-finetune/scripts/run_finetune.py:1391`)
- **MEDIUM** SECURITY/Session Persistence (RA2): Rogue Agent: create the MONAI compatibility environment under `~/.cache/nvidia-skills/venvs/nv-segment-ct-finetune-monai14/`; may cache model assets under `~/.cache (`SKILL.md:59`)
- **MEDIUM** SECURITY/Autonomous Decision Making (EA2): Excessive Agency: without checking (`SKILL.md:203`)
- 23 additional finding(s) are available in the full evaluation artifacts.

</details>

## Scoring Methodology

<details>
<summary>Show dimension definitions, source signals, and thresholds</summary>

| Dimension | Question | Scored signals |
|---|---|---|
| Security | Is it safe to use? | `security` (100%) |
| Correctness | Is the answer correct? | `accuracy` (100%) |
| Discoverability | Was the right skill loaded when needed? | `skill_execution` (100%) |
| Effectiveness | Did the skill help complete the task? | `goal_accuracy` (50%) + `behavior_check` (50%) |
| Efficiency | Did it avoid wasted tool calls and token usage? | `skill_efficiency` (50%) + `token_efficiency` (50%) |

- Dimension bands: PASS at 50% or above; NEUTRAL from 40% to below 50%; FAIL below 40%.
- Overall Tier 3 lift: PASS at +5 points or more; FAIL at -10 points or less; values between those bands are NEUTRAL.
- Overall verdict: PASS only when every configured dimension passes for at least one supported agent. Lift is reported as diagnostic evidence and does not override this gate.
- The 50% attempt pass threshold is a separate per-task gate; it is not the dimension pass threshold.
- Effectiveness is the equal-weight mean of goal completion (`goal_accuracy`) and expected workflow adherence (`behavior_check`).
- Efficiency is 50% tool-call productivity (the backward-compatible `skill_efficiency` wire id) and 50% `token_efficiency`. Positive-case skill routing is scored under Discoverability, not Efficiency; a negative case without a routing target is N/A. N/A sources are omitted, remaining weights are renormalized, and the dimension is marked partial.

Signals present in this run:

- `security` (Security): unsafe operations, secret leakage, and unauthorized access.
- `skill_execution` (Skill Execution): whether the expected skill was selected, decoys were avoided, and the workflow executed.
- `skill_efficiency` (Tool Productivity): tool-call productivity (legacy wire id; routing is scored under Discoverability).
- `accuracy` (Accuracy): final-answer correctness against the reference answer.
- `goal_accuracy` (Goal Accuracy): whether the user's goal was achieved.
- `behavior_check` (Behavior Check): whether the expected workflow behavior was followed.
- `token_efficiency` (Token Efficiency): actual uncached prompt plus completion usage (50% of Efficiency).

</details>

## Freshness

Regenerate this benchmark when the skill, evaluation dataset, target agent/model, evaluator version, environment, or scoring policy changes.
