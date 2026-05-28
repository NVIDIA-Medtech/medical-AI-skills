## Description: <br>
Used for generating synthetic CT volumes and masks with NV-Generate-CTMR rflow-ct. Not for production training data without review. <br>

This skill is for research and development only. <br>

## Owner
NVIDIA <br>

### License/Terms of Use: <br>
Apache 2.0 <br>
## Use Case: <br>
Developers and researchers use this skill to generate synthetic CT volumes and paired segmentation masks for medical imaging research, algorithm development, and data augmentation workflows. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: Review before execution as proposals could introduce incorrect or misleading guidance into skills. <br>
Mitigation: Review and scan skill before deployment. <br>

## Reference(s): <br>
- [NV-Generate-CTMR upstream repository](https://github.com/NVIDIA-Medtech/NV-Generate-CTMR) <br>
- [FOV and download references](references/fov-and-downloads.md) <br>
- [CT mask label space](references/ct-mask-label-space.md) <br>
- [CT from mask format](references/ct-from-mask-format.md) <br>


## Skill Output: <br>
**Output Type(s):** [Files, JSON] <br>
**Output Format:** [NIfTI volumes and structured JSON result with HTML summary card] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Paired CT image and mask NIfTI volumes, result JSON with label mapping, geometry metadata, and verifier guidance] <br>

## Evaluation Metrics Used: <br>
Reported benchmark dimensions: <br>
- Security: Checks whether skill-assisted execution avoids unsafe behavior such as secret leakage, destructive commands, or unauthorized access. <br>
- Correctness: Checks whether the agent follows the expected workflow and produces the correct final output. <br>
- Discoverability: Checks whether the agent loads the skill when relevant and avoids using it when irrelevant. <br>
- Effectiveness: Checks whether the agent performs measurably better with the skill than without it. <br>
- Efficiency: Checks whether the agent uses fewer tokens and avoids redundant work. <br>



## Skill Version(s): <br>
58b9ee3 (source: git SHA, committed 2026-05-28) <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
