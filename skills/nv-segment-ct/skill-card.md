## Description: <br>
Used for running NV-Segment-CT VISTA3D on CT NIfTI volumes and recording label-map evidence. <br>

This skill is for research and development only. <br>

## Owner
NVIDIA <br>

### License/Terms of Use: <br>
Apache-2.0 <br>
## Use Case: <br>
Developers and medtech engineers use this skill to run VISTA3D segmentation on CT NIfTI volumes and generate structured label-map evidence for engineering verification workflows. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: Review before execution as proposals could introduce incorrect or misleading guidance into skills. <br>
Mitigation: Review and scan skill before deployment. <br>

## Reference(s): <br>
- [NV-Segment-CT on Hugging Face](https://huggingface.co/nvidia/NV-Segment-CT) <br>
- [Medical Decathlon (MSD09 Spleen fixture source)](http://medicaldecathlon.com/) <br>


## Skill Output: <br>
**Output Type(s):** [JSON, Files] <br>
**Output Format:** [Structured JSON evidence summary and NIfTI label-map file] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Output includes per-class voxel counts, physical volumes, mask geometry checks, and artifact validation flags] <br>

## Evaluation Tasks: <br>
NVSkills-Eval 3-Tier evaluation (external profile): Tier 1 static validation (9 checks), Tier 2 deduplication (2 checks). Tier 3 live agent evaluation not available. <br>

## Evaluation Metrics Used: <br>
Reported benchmark dimensions: <br>
- Security: Checks whether skill-assisted execution avoids unsafe behavior such as secret leakage, destructive commands, or unauthorized access. <br>
- Correctness: Checks whether the agent follows the expected workflow and produces the correct final output. <br>
- Discoverability: Checks whether the agent loads the skill when relevant and avoids using it when irrelevant. <br>
- Effectiveness: Checks whether the agent performs measurably better with the skill than without it. <br>
- Efficiency: Checks whether the agent uses fewer tokens and avoids redundant work. <br>



## Evaluation Results: <br>
| Tier | Checks | Findings | Verdict |
|---|---:|---:|---|
| Tier 1: Static Validation | 9 | 7 | PASS (with observations) |
| Tier 2: Deduplication | 2 | 0 | PASS |
| Overall | — | — | PASS |

## Skill Version(s): <br>
b00e8b7 (source: git SHA, committed 2026-05-28) <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
