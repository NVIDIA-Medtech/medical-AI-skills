## Description: <br>
Used for converting one CT DICOM series folder to a HU NIfTI volume with affine evidence. <br>

This skill is for research and development only. <br>

## Owner
NVIDIA <br>

### License/Terms of Use: <br>
Apache-2.0 <br>
## Use Case: <br>
Developers and engineers use this skill to convert a single CT DICOM series directory to a Hounsfield-unit-scaled NIfTI volume with computed affine and orientation metadata for engineering verification workflows. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: Review before execution as proposals could introduce incorrect or misleading guidance into skills. <br>
Mitigation: Review and scan skill before deployment. <br>

## Reference(s): <br>
- [Skill Manifest](skill_manifest.yaml) <br>
- [Output Schema](validators/output_schema.json) <br>


## Skill Output: <br>
**Output Type(s):** [Files, JSON] <br>
**Output Format:** [NIfTI volume (.nii.gz) and JSON summary] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [None] <br>

## Evaluation Agents Used: <br>
- `claude-code` <br>
- `codex` <br>



## Evaluation Tasks: <br>
Evaluated against 2 evaluation tasks (1 positive skill-activation, 1 negative) with 2 attempts per task. Pass threshold: 50%. Overall verdict: PASS. <br>

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
| Correctness | 4 | 100% (+11%) | 88% (+1%) |
| Discoverability | 4 | 97% (-2%) | 86% (+4%) |
| Effectiveness | 4 | 92% (+10%) | 74% (+6%) |
| Efficiency | 4 | 84% (+0%) | 76% (+13%) |

## Skill Version(s): <br>
0.1.0 (source: skill_manifest.yaml) <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
