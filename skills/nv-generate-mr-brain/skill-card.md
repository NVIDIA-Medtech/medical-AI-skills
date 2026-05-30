## Description: <br>
Used for generating synthetic brain MRI volumes with NV-Generate-CTMR rflow-mr-brain. Not for production training data. <br>

This skill is for research and development only. <br>

## Owner
NVIDIA <br>

### License/Terms of Use: <br>
Apache 2.0 <br>
## Use Case: <br>
Developers and researchers generating synthetic brain MRI volumes for research, testing, and model development workflows. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: Review before execution as proposals could introduce incorrect or misleading guidance into skills. <br>
Mitigation: Review and scan skill before deployment. <br>

## Reference(s): <br>
- [NV-Generate-CTMR MR Brain Image Generation](https://github.com/NVIDIA-Medtech/NV-Generate-CTMR#22-mr-brain-image-generation) <br>
- [NV-Generate-MR-Brain Model Weights (Hugging Face)](https://huggingface.co/nvidia/NV-Generate-MR-Brain) <br>
- [FOV and Downloads Reference](references/fov-and-downloads.md) <br>


## Skill Output: <br>
**Output Type(s):** [Shell commands, Files, JSON] <br>
**Output Format:** [Markdown with inline bash code blocks and NIfTI volume output] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Generates synthetic NIfTI brain MRI volumes with a JSON result summary including geometry, spacing, affine, and intensity metadata] <br>

## Evaluation Agents Used: <br>
- Claude Code (`claude-code`) <br>
- Codex (`codex`) <br>



## Evaluation Tasks: <br>
Evaluated against 2 evaluation tasks with 2 attempts per task; pass threshold 50%. <br>

## Evaluation Metrics Used: <br>
Reported benchmark dimensions: <br>
- Security: Checks whether skill-assisted execution avoids unsafe behavior such as secret leakage, destructive commands, or unauthorized access. <br>
- Correctness: Checks whether the agent follows the expected workflow and produces the correct final output. <br>
- Discoverability: Checks whether the agent loads the skill when relevant and avoids using it when irrelevant. <br>
- Effectiveness: Checks whether the agent performs measurably better with the skill than without it. <br>
- Efficiency: Checks whether the agent uses fewer tokens and avoids redundant work. <br>

Underlying evaluation signals used in this run: <br>
- `security`: Checks for unsafe operations, secret leakage, and unauthorized access. <br>
- `skill_execution`: Verifies that the agent loaded the expected skill and workflow. <br>
- `skill_efficiency`: Checks routing quality, decoy avoidance, and redundant tool usage. <br>
- `accuracy`: Grades final-answer correctness against the reference answer. <br>
- `goal_accuracy`: Checks whether the overall user task completed successfully. <br>
- `behavior_check`: Verifies expected behavior steps, including safety expectations. <br>
- `token_efficiency`: Compares token usage with and without the skill. <br>



## Evaluation Results: <br>
| Dimension | Num | `claude-code` | `codex` |
|---|---:|---:|---:|
| Security | 4 | 100% (+0%) | 100% (+0%) |
| Correctness | 4 | 86% (-9%) | 96% (+40%) |
| Discoverability | 4 | 61% (-35%) | 72% (+9%) |
| Effectiveness | 4 | 81% (+9%) | 78% (+47%) |
| Efficiency | 4 | 45% (-33%) | 57% (+3%) |

## Skill Version(s): <br>
ac94e25 (source: git SHA, committed 2026-05-30) <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
