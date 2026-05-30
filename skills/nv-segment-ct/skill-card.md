## Description: <br>
Used for running NV-Segment-CT VISTA3D on CT NIfTI volumes and recording label-map evidence. <br>

This skill is for research and development only. <br>

## Owner
NVIDIA <br>

### License/Terms of Use: <br>
Apache-2.0 <br>
## Use Case: <br>
Developers and engineers use this skill to invoke NVIDIA VISTA3D CT segmentation on NIfTI volumes for engineering verification and development workflows. Not for clinical deployment or interpretation. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: Review before execution as proposals could introduce incorrect or misleading guidance into skills. <br>
Mitigation: Review and scan skill before deployment. <br>

## Reference(s): <br>
- [NVIDIA NV-Segment-CT on Hugging Face](https://huggingface.co/nvidia/NV-Segment-CT) <br>


## Skill Output: <br>
**Output Type(s):** [Files, JSON] <br>
**Output Format:** [NIfTI label-map file and structured JSON evidence summary] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Includes per-class voxel counts, physical volumes, geometry validation, and artifact checks] <br>

## Evaluation Agents Used: <br>
- Claude Code (`claude-code`) <br>
- Codex (`codex`) <br>



## Evaluation Tasks: <br>
Evaluated against 2 evaluation tasks (1 positive skill-activation, 1 negative). 2 attempts per task, 50% pass threshold. <br>

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
| Security | 4 | 75% (-25%) | 100% (+0%) |
| Correctness | 4 | 89% (-6%) | 91% (+4%) |
| Discoverability | 4 | 93% (+5%) | 79% (+4%) |
| Effectiveness | 4 | 72% (-12%) | 81% (+3%) |
| Efficiency | 4 | 84% (+10%) | 70% (+9%) |

## Skill Version(s): <br>
0.2.0 (source: skill_manifest.yaml) <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
