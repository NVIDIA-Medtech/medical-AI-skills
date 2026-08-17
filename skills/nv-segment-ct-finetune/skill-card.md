## Description: <br>
Used for smoke or dataset finetuning of NV-Segment-CT VISTA3D on CT NIfTI labels. Not for clinical validation. <br>

This skill is for research and development only. <br>

## Owner
NVIDIA <br>

### License/Terms of Use: <br>
Apache 2.0 <br>
## Use Case: <br>
Developers and engineers use this skill to fine-tune the NV-Segment-CT VISTA3D segmentation model on custom CT NIfTI datasets for research and development workflows. <br>

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
- [Task06 reference details and results](references/task06-and-results.md) <br>
- [NV-Segment-CTMR upstream repository](https://github.com/NVIDIA-Medtech/NV-Segment-CTMR.git) <br>


## Skill Output: <br>
**Output Type(s):** [Files, Shell commands, Configuration instructions] <br>
**Output Format:** [JSON (schema-validated output.json) with model checkpoint files] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Produces output.json with Dice metrics, checkpoint paths, and runtime diagnostics alongside finetuned model weights] <br>

## Evaluation Agents Used: <br>
- Claude Code (`aws/anthropic/bedrock-claude-opus-4-8`) <br>
- Codex (`openai/openai/gpt-5.5`) <br>



## Evaluation Tasks: <br>
Evaluated against 2 positive evaluation tasks on a trusted local host using evaluator version 1.2.7. <br>

## Evaluation Metrics Used: <br>
Reported benchmark dimensions: <br>
- Security: Checks for unsafe operations, secret leakage, and unauthorized access. <br>
- Correctness: Checks final-answer correctness against the reference answer. <br>
- Discoverability: Checks whether the expected skill was found and executed when needed. <br>
- Effectiveness: Checks whether the skill helped complete the user's goal and expected workflow (goal_accuracy 50% + behavior_check 50%). <br>
- Efficiency: Checks routing quality, workspace-aware skill reads, and productive tool use. <br>

Underlying evaluation signals used in this run: <br>
- `security`: Detects unsafe operations, secret leakage, and unauthorized access. <br>
- `accuracy`: Verifies final-answer correctness against the reference answer. <br>
- `skill_execution`: Verifies whether the expected skill was found and executed. <br>
- `goal_accuracy`: Verifies whether the user's goal was achieved. <br>
- `behavior_check`: Verifies whether the expected workflow behavior was followed. <br>
- `skill_efficiency`: Verifies routing quality, workspace-aware skill reads, and productive tool use. <br>



## Evaluation Results: <br>
| Measure | Claude Code (Baseline → Skill) | Codex (Baseline → Skill) |
|---|---:|---:|
| Overall | 53% → 83% (+29 pts) | 72% → 88% (+15 pts) |
| Security | 100% → 100% (±0 pts) | 50% → 100% (+50 pts) |
| Correctness | 30% → 90% (+60 pts) | 100% → 100% (±0 pts) |
| Discoverability | 47% → 88% (+41 pts) | 59% → 81% (+22 pts) |
| Effectiveness | 50% → 50% (±0 pts) | 91% → 72% (-19 pts) |
| Efficiency | 39% → 85% (+46 pts) | 61% → 84% (+23 pts) |

## Skill Version(s): <br>
3e1cfc0 (source: git SHA, committed 2026-08-17) <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
