## Description: <br>
Used for command-shape or live NV-Reason-CXR chest X-ray reasoning smoke tests. Not for diagnosis or clinical reporting. <br>

This skill is for research and development only. <br>

## Owner
NVIDIA <br>

### License/Terms of Use: <br>
Apache 2.0 <br>
## Use Case: <br>
Developers and medtech engineers use this skill to run NV-Reason-CXR-3B chest X-ray inference for research and development, producing structured JSON engineering evidence. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: Review before execution as proposals could introduce incorrect or misleading guidance into skills. <br>
Mitigation: Review and scan skill before deployment. <br>

## Reference(s): <br>
- [NV-Reason-CXR GitHub Repository](https://github.com/NVIDIA-Medtech/NV-Reason-CXR) <br>
- [NV-Reason-CXR-3B Hugging Face Model](https://huggingface.co/nvidia/NV-Reason-CXR-3B) <br>


## Skill Output: <br>
**Output Type(s):** [JSON] <br>
**Output Format:** [JSON] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Structured response with input image metadata, prompt, response text, runtime identity, and limitations] <br>

## Evaluation Tasks: <br>
NVSkills-Eval external profile: 9 Tier 1 static validation checks and 2 Tier 2 deduplication checks. Overall verdict: PASS. Tier 3 live agent evaluation not available in this report. <br>

## Evaluation Metrics Used: <br>
Reported benchmark dimensions: <br>
- Security: Checks whether skill-assisted execution avoids unsafe behavior such as secret leakage, destructive commands, or unauthorized access. <br>
- Correctness: Checks whether the agent follows the expected workflow and produces the correct final output. <br>
- Discoverability: Checks whether the agent loads the skill when relevant and avoids using it when irrelevant. <br>
- Effectiveness: Checks whether the agent performs measurably better with the skill than without it. <br>
- Efficiency: Checks whether the agent uses fewer tokens and avoids redundant work. <br>



## Skill Version(s): <br>
0.1.0 (source: skill_manifest.yaml) <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
