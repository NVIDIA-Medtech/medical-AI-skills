# Skill Benchmark: miagent

> ✅ **Overall verdict: PASS — Recommended for publication**

## Publication Recommendation

Recommended for publication based on the completed evaluation evidence in this report.

## Evaluation Metadata

- Skill: `miagent`
- Validation status: `passed`
- Evaluation date: 2026-11-12
- Evaluator version: `1.6.9`
- Agents: Claude Code (`aws/anthropic/bedrock-claude-opus-5-5`), Codex (`openai/openai/gpt-6.1-sol`)
- Tasks: 8 evaluation tasks (6 positive, 2 negative)
- Dataset digest: `sha256:0c31f8fd3e3d2f6540f475e24bff2496decaeb7884a728ef61f62258267f2e3d` (skill-evaluator-dataset-snapshot/1)
- Attempts per task: 1
- Environment: `k8s-sandbox`
- Tier 2 evidence: required for publication
- Tier 3 evidence: required for publication

Each task attempt ran in its own isolated sandbox pod.

## Tier 1 LLM Provenance

SkillSpector provider, model, analyzer revision, and determinism evidence retained for this scan.

| Skill | Provider | Adapter | Analyzer | Model | Revision | Determinism |
| --- | --- | --- | --- | --- | --- | --- |
| miagent | nv_inference | openai | mcp_tool_poisoning | `aws/anthropic/bedrock-claude-opus-5-5` | `2.13.4` | nondeterministic / provider_defaults |
| miagent | nv_inference | openai | semantic_developer_intent | `aws/anthropic/bedrock-claude-opus-5-5` | `2.13.4` | nondeterministic / provider_defaults |
| miagent | nv_inference | openai | semantic_quality_policy | `aws/anthropic/bedrock-claude-opus-5-5` | `2.13.4` | nondeterministic / provider_defaults |
| miagent | nv_inference | openai | semantic_security_discovery | `aws/anthropic/bedrock-claude-opus-5-5` | `2.13.4` | nondeterministic / provider_defaults |
| miagent | nv_inference | openai | meta_analyzer | `aws/anthropic/bedrock-claude-opus-5-5` | `2.13.4` | nondeterministic / provider_defaults |

- Controls for `miagent`: temperature=not set (source=provider_default, forwarded=no); seed=not set (source=unset, forwarded=no); reasoning_effort=not set (source=provider_default, forwarded=no)

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
| Overall | 85.4% — baseline ran, but no comparable score was available; uplift unavailable | 89.4% — baseline ran, but no comparable score was available; uplift unavailable |
| Security | 100.0% → 87.5% (-12.5 points) | 75.0% → 100.0% (+25.0 points) |
| Correctness | 55.0% → 95.0% (+40.0 points) | 40.0% → 97.5% (+57.5 points) |
| Discoverability | 80.0% — baseline ran, but no comparable score was available; uplift unavailable | 88.3% — baseline ran, but no comparable score was available; uplift unavailable |
| Effectiveness | 47.4% → 70.3% (+22.9 points) | 42.7% → 71.4% (+28.7 points) |
| Efficiency | 94.3% — baseline ran, but no comparable score was available; uplift unavailable | 89.8% — baseline ran, but no comparable score was available; uplift unavailable |

**How to read this table:** baseline is the same task attempted without the target skill. Scores are rounded to one decimal; threshold-adjacent values use additional precision so their displayed band matches the verdict. Uplift is derived from those displayed scores and shown in percentage points.

Example: `47.0% → 92.0% (+45.0 points)` means the skill-assisted run scored 92.0%, 45.0 percentage points above its 47.0% no-skill baseline.

A partial dimension was calculated from only the available configured signals; review the detailed report before relying on it.

### Comparison details

Shared-source comparisons use the same signals and weights on both conditions. They do not replace the full dimension scores above or change the publication verdict.

| Agent | Dimension | Basis | Baseline → With skill (uplift) | Explanation |
| --- | --- | --- | --- | --- |
| claude-code | Discoverability | Dimension comparison | N/A | Discoverability is not applicable to the no-skill baseline; there is no installed skill to discover. |
| claude-code | Efficiency | Token-only comparison | 98.3% → 95.3% (-3.0 points) | Only Token Efficiency is comparable; the full dimension scores use different evaluator sources. |
| codex | Discoverability | Dimension comparison | N/A | Discoverability is not applicable to the no-skill baseline; there is no installed skill to discover. |
| codex | Efficiency | Token-only comparison | 90.9% → 87.9% (-3.0 points) | Only Token Efficiency is comparable; the full dimension scores use different evaluator sources. |

## Token Usage

Actual Tier 3 execution usage is reported for every observed agent/case pair and both conditions.

| Agent | Dataset case | With skill | Without skill | Delta | Change | Coverage |
|---|---|---:|---:|---:|---:|---|
| claude-code | All cases | 1,643,686 | 1,046,293 | +597,393 | +57.10% | skill 8/8; base 8/8 |
| claude-code | execution-failure-is-not-result | 164,448 | 144,076 | +20,372 | +14.14% | skill 1/1; base 1/1 |
| claude-code | initialize-only | 440,891 | 107,165 | +333,726 | +311.41% | skill 1/1; base 1/1 |
| claude-code | negative-clinical-decision | 35,349 | 106,899 | -71,550 | -66.93% | skill 1/1; base 1/1 |
| claude-code | negative-single-inference | 144,583 | 143,428 | +1,155 | +0.81% | skill 1/1; base 1/1 |
| claude-code | plateau-external-loop | 163,443 | 107,138 | +56,305 | +52.55% | skill 1/1; base 1/1 |
| claude-code | protected-label-proposal | 35,608 | 35,506 | +102 | +0.29% | skill 1/1; base 1/1 |
| claude-code | research-before-method | 445,339 | 107,881 | +337,458 | +312.81% | skill 1/1; base 1/1 |
| claude-code | resume-existing-authority | 214,025 | 294,200 | -80,175 | -27.25% | skill 1/1; base 1/1 |
| codex | All cases | 1,059,240 | 395,915 | +663,325 | +167.54% | skill 8/8; base 8/8 |
| codex | execution-failure-is-not-result | 112,878 | 59,048 | +53,830 | +91.16% | skill 1/1; base 1/1 |
| codex | initialize-only | 84,026 | 70,848 | +13,178 | +18.60% | skill 1/1; base 1/1 |
| codex | negative-clinical-decision | 29,198 | 17,501 | +11,697 | +66.84% | skill 1/1; base 1/1 |
| codex | negative-single-inference | 57,167 | 60,366 | -3,199 | -5.30% | skill 1/1; base 1/1 |
| codex | plateau-external-loop | 67,375 | 44,946 | +22,429 | +49.90% | skill 1/1; base 1/1 |
| codex | protected-label-proposal | 61,723 | 13,413 | +48,310 | +360.17% | skill 1/1; base 1/1 |
| codex | research-before-method | 531,158 | 88,575 | +442,583 | +499.67% | skill 1/1; base 1/1 |
| codex | resume-existing-authority | 115,715 | 41,218 | +74,497 | +180.74% | skill 1/1; base 1/1 |
| ALL AGENTS | Dataset aggregate | 2,702,926 | 1,442,208 | +1,260,718 | +87.42% | skill 16/16; base 16/16 |

Prompt tokens include cached reads, so total tokens are `prompt + completion` (cached is not added twice). The Efficiency score uses `(prompt - cached) + completion`. Change is `100 * (with - without) / without`; negative means fewer tokens. N/A comparisons include their reason in the coverage column; coverage is never estimated.

## Tier Status

| Tier | Purpose | Status | Evidence |
|---|---|---|---|
| Tier 1 | Static validation | **PASSED WITH OBSERVATIONS** | 11 validator(s); 16 finding(s) |
| Tier 2 | Semantic deduplication | **PASSED** | 2 validator(s); 0 finding(s) |
| Tier 3 | Live agent evaluation | **PASS** | 2 agent(s); 8 task(s) |

## Findings and Observations

<details>
<summary>Show detailed findings and successful checks</summary>

- **MEDIUM** QUALITY/quality_efficiency: Large skill (5312 tokens, recommended max <5000). Per agentskills.io, SKILL.md should be concise (~500 lines) — large skill bodies increase token cost after invocation; long or unfocused top-level descriptions can degrade agent routing accuracy (`skills/miagent/SKILL.md`)
- **MEDIUM** SCHEMA/body_recommended_section: Missing recommended section: '## Examples' (`skills/miagent/SKILL.md`)
- **MEDIUM** SCRIPT_LINT/deep_nesting: check_consistency.py has deeply nested code (depth 7, max 6) (`skills/miagent/scripts/check_consistency.py`)
- **MEDIUM** SECURITY/subprocess module call (AST4): Dangerous Code Execution: subprocess.run(
        [sys.executable, str(ROOT / "scripts" / name), *map(str, args)],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    ) (`tests/test_skill.py:32`)
- **MEDIUM** SECURITY/subprocess module call (AST4): Dangerous Code Execution: subprocess.run(
        [
            sys.executable,
            str(package / "scripts/init_challenge.py"),
            str(package / "fixtures/request.json"),
            "--output-dir",
           (`tests/test_skill.py:117`)
- 11 additional finding(s) are available in the full evaluation artifacts.

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
