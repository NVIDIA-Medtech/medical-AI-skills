## Description: <br>
Used for converting one CT DICOM series folder to a HU NIfTI volume with affine evidence. Not for multi-frame DICOM or clinical use. <br>

This skill is for research and development only. <br>

## Owner
NVIDIA <br>

### License/Terms of Use: <br>
Apache-2.0 <br>
## Use Case: <br>
Developers and engineers converting single-series CT DICOM directories to HU-scaled NIfTI volumes with affine and orientation metadata for engineering verification and downstream medical imaging workflows. <br>

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
- [Skill Manifest](skill_manifest.yaml) <br>
- [Output Validation Schema](validators/output_schema.json) <br>


## Skill Output: <br>
**Output Type(s):** [Files, Analysis] <br>
**Output Format:** [NIfTI volume (.nii.gz) and JSON summary] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Key output fields include n_slices, series_instance_uid, output shape/spacing/axcodes/affine, hu_range, and runtime.conversion_seconds.] <br>

## Evaluation Agents Used: <br>
- Claude Code (`aws/anthropic/bedrock-claude-opus-4-8`) <br>
- Codex (`openai/openai/gpt-5.5`) <br>



## Evaluation Tasks: <br>
Evaluated against 2 tasks (1 positive, 1 negative) in isolated sandbox pods using evaluator version 1.3.2. <br>

## Evaluation Metrics Used: <br>
Reported benchmark dimensions: <br>
- Security: Whether the skill is safe to use, checking for unsafe operations, secret leakage, and unauthorized access. <br>
- Correctness: Whether the skill produces correct answers against the reference answer. <br>
- Discoverability: Whether the right skill was found and executed when needed. <br>
- Effectiveness: Whether the skill helped complete the user's goal and expected workflow (equal-weight mean of goal completion and behavior adherence). <br>
- Efficiency: Whether the skill avoided wasted tool or skill usage through quality routing and productive tool use. <br>

Underlying evaluation signals used in this run: <br>
- `security`: Checks for unsafe operations, secret leakage, and unauthorized access. <br>
- `skill_execution`: Verifies the expected skill was found and executed. <br>
- `accuracy`: Final-answer correctness against the reference answer. <br>
- `goal_accuracy`: Whether the user's goal was achieved. <br>
- `behavior_check`: Whether the expected workflow behavior was followed. <br>
- `skill_efficiency`: Routing quality, workspace-aware skill reads, and productive tool use. <br>



## Evaluation Results: <br>
| Measure | Claude Code (Baseline → Skill Uplift) | Codex (Baseline → Skill Uplift) |
|---|---:|---:|
| Overall | 69% → 93% (+24 points) | 84% → 97% (+13 points) |
| Security | 100% → 100% (±0 points) | 50% → 100% (+50 points) |
| Correctness | 50% → 100% (+50 points) | 100% → 100% (±0 points) |
| Discoverability | 72% → 91% (+19 points) | 84% → 91% (+6 points) |
| Effectiveness | 52% → 82% (+30 points) | 96% → 100% (+4 points) |
| Efficiency | 71% → 93% (+22 points) | 87% → 92% (+5 points) |

## Skill Version(s): <br>
0.1.0 (source: skill_manifest.yaml) <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
