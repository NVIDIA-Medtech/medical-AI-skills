## Description: <br>
Exports sanitized metadata, parameters, reproducibility details, quality metrics, and optional review artifacts from Medical AI inference runs or evidence packs to MLflow. <br>

This skill is ready for commercial/non-commercial use. <br>

## Owner
NVIDIA <br>

### License/Terms of Use: <br>
Apache 2.0 <br>
## Use Case: <br>
Developers and engineers use this skill to export sanitized inference-run metadata, quality metrics, reproducibility parameters, and review artifacts from Medical AI evidence packs to MLflow for post-hoc tracking and audit. <br>

### Deployment Geography for Use: <br>
Global <br>

## Requirements / Dependencies: <br>
**Requires API Key or External Credential:** [Optional] <br>
**Credential Type(s):** [API key] <br>

Do not include secrets in prompts/logs/output; use least-privilege credentials; rotate keys as appropriate. <br>

## Known Risks and Mitigations: <br>
Risk: Review before execution as proposals could introduce incorrect or misleading guidance into skills. <br>
Mitigation: Review and scan skill before deployment. <br>

## Reference(s): <br>
- [Output schema](validators/output_schema.json) <br>
- [Skill manifest](skill_manifest.yaml) <br>
- [Evaluation benchmark](BENCHMARK.md) <br>


## Skill Output: <br>
**Output Type(s):** [Analysis, API Calls] <br>
**Output Format:** [JSON] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Dry-run mode produces a preview without contacting MLflow; live modes log runs via the MLflow Python API] <br>

## Evaluation Agents Used: <br>
- Claude Code (`aws/anthropic/bedrock-claude-opus-4-8`) <br>
- Codex (`openai/openai/gpt-5.5`) <br>



## Evaluation Tasks: <br>
4 evaluation tasks (2 positive, 2 negative), each in an isolated k8s-sandbox pod. Evaluator version 1.3.2, Tier 3 live agent evaluation. <br>

## Evaluation Metrics Used: <br>
Reported benchmark dimensions: <br>
- Security: Checks for unsafe operations, secret leakage, and unauthorized access. <br>
- Correctness: Validates final-answer correctness against the reference answer. <br>
- Discoverability: Measures whether the expected skill was found and executed when needed. <br>
- Effectiveness: Equal-weight mean of goal completion and expected workflow adherence. <br>
- Efficiency: Evaluates routing quality, workspace-aware skill reads, and productive tool use. <br>

Underlying evaluation signals used in this run: <br>
- `security`: Detects unsafe operations, secret leakage, and unauthorized access. <br>
- `skill_execution`: Verifies the expected skill was found and executed. <br>
- `skill_efficiency`: Measures routing quality, workspace-aware skill reads, and productive tool use. <br>
- `accuracy`: Checks final-answer correctness against the reference answer. <br>
- `goal_accuracy`: Assesses whether the user's goal was achieved. <br>
- `behavior_check`: Verifies expected workflow behavior was followed. <br>



## Evaluation Results: <br>
| Measure | Claude Code (Baseline → Skill Uplift) | Codex (Baseline → Skill Uplift) |
|---|---:|---:|
| Overall | 70% → 97% (+27 points) | 69% → 97% (+28 points) |
| Security | 100% → 100% (±0 points) | 100% → 100% (±0 points) |
| Correctness | 55% → 100% (+45 points) | 55% → 100% (+45 points) |
| Discoverability | 75% → 98% (+23 points) | 66% → 92% (+27 points) |
| Effectiveness | 50% → 87% (+37 points) | 54% → 96% (+42 points) |
| Efficiency | 70% → 98% (+28 points) | 71% → 98% (+26 points) |

## Skill Version(s): <br>
0.2.0 (source: skill_manifest.yaml) <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
