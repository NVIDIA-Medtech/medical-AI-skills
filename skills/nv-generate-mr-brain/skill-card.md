## Description: <br>
Used for generating synthetic brain MRI volumes with NV-Generate-CTMR rflow-mr-brain. Not for production training data. <br>

This skill is for research and development only. <br>

## Owner
NVIDIA <br>

### License/Terms of Use: <br>
Apache 2.0 <br>
## Use Case: <br>
Developers and engineers generating synthetic brain MRI volumes for research, engineering validation, and development workflows using the NV-Generate-CTMR rflow-mr-brain pipeline. <br>

### Deployment Geography for Use: <br>
Global <br>

## Requirements / Dependencies: <br>
**Requires API Key or External Credential:** [Not Specified] <br>
**Credential Type(s):** [None identified] <br>

Do not include secrets in prompts/logs/output; use least-privilege credentials; rotate keys as appropriate. <br>

## Known Risks and Mitigations: <br>
Risk: Review before execution as proposals could introduce incorrect or misleading guidance into skills. <br>
Mitigation: Review and scan skill before deployment. <br>

## Reference(s): <br>
- [FOV and Downloads](references/fov-and-downloads.md) <br>
- [NV-Generate-CTMR MR Brain Image Generation](https://github.com/NVIDIA-Medtech/NV-Generate-CTMR#22-mr-brain-image-generation) <br>
- [NV-Generate-MR-Brain Model (Hugging Face)](https://huggingface.co/nvidia/NV-Generate-MR-Brain) <br>


## Skill Output: <br>
**Output Type(s):** [Shell commands, Files, JSON] <br>
**Output Format:** [Markdown with inline bash code blocks and JSON result summary] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Generated NIfTI volumes under caller-provided output directory; structured JSON result with geometry, spacing, and quality checks] <br>

## Evaluation Agents Used: <br>
- claude-code <br>
- codex <br>



## Evaluation Tasks: <br>
Evaluated against 2 evaluation tasks in the astra-sandbox environment using the NVSkills-Eval external profile. <br>

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
| Security | 2 | 100% (+50%) | 100% (+0%) |
| Correctness | 2 | 78% (+44%) | 74% (+63%) |
| Discoverability | 2 | 93% (+47%) | 89% (+71%) |
| Effectiveness | 2 | 38% (+22%) | 40% (+35%) |
| Efficiency | 2 | 79% (+31%) | 86% (+53%) |

## Skill Version(s): <br>
0.1.0 (source: skill_manifest.yaml) <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
