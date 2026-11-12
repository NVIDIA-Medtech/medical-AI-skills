## Description: <br>
Used for MIAgent medical-imaging research, experiment planning, diagnosis, and resumable optimization. Not for clinical decisions or standalone model inference. <br>

This skill is for research and development only. <br>

## Owner
NVIDIA <br>

### License/Terms of Use: <br>
Apache 2.0 <br>
## Use Case: <br>
Developers, engineers, and researchers use this skill to have a host agent run the MIAgent v3.5 medical-imaging research workflow: initializing a durable, human-inspectable task record, then performing research, candidate selection, implementation planning, experiments, and resumable optimization. Engineering and research use only; not for clinical decision support or autonomous diagnosis. <br>

### Deployment Geography for Use: <br>
Global <br>

## Requirements / Dependencies: <br>
**Requires API Key or External Credential:** [No] <br>
**Credential Type(s):** [None] <br>

Do not include secrets in prompts/logs/output; use least-privilege credentials; rotate keys as appropriate. <br>

## Known Risks and Mitigations: <br>
Risk: Review before execution as proposals could introduce incorrect or misleading guidance into skills. <br>
Mitigation: Review and scan skill before deployment. <br>

## Reference(s): <br>
- [Critic Review](references/critic-review.md) <br>
- [Result Analysis](references/result-analysis.md) <br>
- [Segmentation Result Analysis](references/segmentation-analysis.md) <br>
- [Registration Result Analysis](references/registration-analysis.md) <br>
- [Generation And Synthesis Result Analysis](references/generation-analysis.md) <br>
- [Representation Learning Result Analysis](references/representation-analysis.md) <br>
- [Medical VLM Result Analysis](references/vlm-analysis.md) <br>
- [MIAgent v3.5 upstream source (provenance)](https://github.com/heyufan1995/MIAgent) <br>


## Skill Output: <br>
**Output Type(s):** [Files, Analysis, Shell commands] <br>
**Output Format:** [JSON initialization report on stdout plus Markdown research records (challenge, dashboard, trajectory, and later workflow artifacts)] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Initialization creates only three records and launches no experiments; run artifacts are written to the caller's workspace, never into the installed skill.] <br>

## Evaluation Agents Used: <br>
- Claude Code (`aws/anthropic/bedrock-claude-opus-5-5`) <br>
- Codex (`openai/openai/gpt-6.1-sol`) <br>



## Evaluation Tasks: <br>
8 evaluation tasks (6 positive, 2 negative), 1 attempt per task, each in its own isolated sandbox pod (`k8s-sandbox`); dataset digest `sha256:0c31f8fd3e3d2f6540f475e24bff2496decaeb7884a728ef61f62258267f2e3d` (skill-evaluator-dataset-snapshot/1). Cases: execution-failure-is-not-result, initialize-only, negative-clinical-decision, negative-single-inference, plateau-external-loop, protected-label-proposal, research-before-method, resume-existing-authority. Each task was also attempted without the skill as a baseline. <br>

## Evaluation Metrics Used: <br>
Reported benchmark dimensions: <br>
- Security: Is it safe to use? Scored from `security` (100%). <br>
- Correctness: Is the answer correct? Scored from `accuracy` (100%). <br>
- Discoverability: Was the right skill loaded when needed? Scored from `skill_execution` (100%). <br>
- Effectiveness: Did the skill help complete the task? Scored from `goal_accuracy` (50%) + `behavior_check` (50%). <br>
- Efficiency: Did it avoid wasted tool calls and token usage? Scored from `skill_efficiency` (50%) + `token_efficiency` (50%). <br>

Underlying evaluation signals used in this run: <br>
- `security`: Security: unsafe operations, secret leakage, and unauthorized access. <br>
- `skill_execution`: Skill Execution: whether the expected skill was selected, decoys were avoided, and the workflow executed. <br>
- `skill_efficiency`: Tool Productivity: tool-call productivity (legacy wire id; routing is scored under Discoverability). <br>
- `accuracy`: Accuracy: final-answer correctness against the reference answer. <br>
- `goal_accuracy`: Goal Accuracy: whether the user's goal was achieved. <br>
- `behavior_check`: Behavior Check: whether the expected workflow behavior was followed. <br>
- `token_efficiency`: Token Efficiency: actual uncached prompt plus completion usage (50% of Efficiency). <br>



## Evaluation Results: <br>
> ✅ **Overall verdict: PASS — Recommended for publication**

### Publication Recommendation

Recommended for publication based on the completed evaluation evidence in this report.

### Results at a Glance

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

### Tier Status

| Tier | Purpose | Status | Evidence |
|---|---|---|---|
| Tier 1 | Static validation | **PASSED WITH OBSERVATIONS** | 11 validator(s); 16 finding(s) |
| Tier 2 | Semantic deduplication | **PASSED** | 2 validator(s); 0 finding(s) |
| Tier 3 | Live agent evaluation | **PASS** | 2 agent(s); 8 task(s) |

## Skill Version(s): <br>
0.1.0 (source: frontmatter, skill_manifest.yaml) <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
