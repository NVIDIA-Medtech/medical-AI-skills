# Skill scope

This page defines what belongs in the public skill catalog. It is the stable
public subset of local strategy notes: practical rules for contributors, not a
roadmap or business positioning document.

## North star

Turn medtech tools into agent-callable capabilities that are easy to use with a
user's own data and easy to trust through explicit contracts, fixtures, and
evidence.

## Admission criteria

A new entry belongs in `skills/` only when it satisfies all of these:

1. **Wraps a real upstream tool.** Call an externally maintained model, CLI,
   bundle, app, SDK, or library through its documented entry point. Do not
   reimplement inference or file-format logic just to make a skill.
2. **Solves a medtech engineering task.** Examples: convert a DICOM series,
   run a segmentation model, benchmark a HoloHub app, extract metadata, or
   produce a structured engineering report. Clinical decisions do not qualify.
3. **Has a contract-worthy failure mode.** The skill should expose something a
   generic command-success check might miss: orientation drift, empty masks,
   PHI leakage, dependency drift, model identity mismatch, invalid artifacts,
   modality mismatch, or claim-boundary leakage.
4. **Can ship safe fixtures.** Use small synthetic/public fixtures or fixture
   manifests that point to data the user obtains locally. Do not commit patient
   data, large medical volumes, model weights, provider logs, or secrets.
5. **Declares behavioral dependencies.** When output behavior depends on an
   installed upstream package or framework, add `validation.env_pin` for the
   direct behavioral dependency.

Skills that fail the upstream-tool rule may still be useful as anti-pattern
examples, but they do not belong in the publishable skill catalog.

## Good fits

- DICOM, NIfTI, DICOM SEG, metadata, and conversion tooling.
- MONAI bundles, NVIDIA-Medtech models, and other medical AI model wrappers.
- Holoscan / HoloHub apps and edge-workflow wrappers.
- Structured LLM-assisted medtech engineering utilities when they emit
  checkable JSON and declare model identity / factual-echo gates.
- Domain verifiers under `verifiers/` when a claim needs a second pass over an
  evidence pack or artifact.

## Out of scope

Do not add these as publishable skills:

- Clinical decision-support skills, diagnosis, treatment recommendation, or
  triage advice.
- Patient-facing chatbots or voice assistants.
- Generic LLM utilities such as summarization or translation unless the task,
  inputs, output schema, and gates are medtech-specific.
- Generic model leaderboards or "best model" benchmark races.
- Generic skill linters, scorers, or evaluators that are not medtech-specific
  Medical AI Skills verifiers.
- Closed proprietary model wrappers without redistributable fixtures or a
  public way to reproduce the evidence path.
- EHR / FHIR write-path skills or hospital deployment integrations.

If a proposal is useful but out of scope, point the contributor to the owning
tooling surface rather than stretching this repo: upstream model repos, Holoscan,
NeMo Agent Toolkit, a deployment platform, or a private integration project.

## Selection, not ranking

The catalog should help users select by declared capability and observed
contract behavior, not rank by performance. `SKILL_INDEX.md`, `find_skills`,
and `compare-skills` should answer:

- Does this skill accept my input format?
- What output artifacts does it produce?
- What side effects, GPU, network, and runtime cost should I expect?
- Which failure modes does its manifest or paired verifier cover?

They should not crown a best model or present clinical performance claims.

