# Agent Skill Best-Practices Rubric

Source: <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices>

Used only for optional Tier 3 advisory review. Deterministic checks live in
`scripts/grade.py`.

## Rubric

- Frontmatter has a specific third-person description.
- `SKILL.md` is concise and tells the agent what to run.
- Examples match the actual wrapped tool.
- Terminology is consistent across docs, manifest, scripts, and output.
- Reference files are one link deep from `SKILL.md`.
- Scripts complete the task directly and return explicit errors.
- Required packages, env vars, network endpoints, and writes are declared.
- Critical operations have machine-readable validation.
- No clinical, diagnostic, patient-facing, regulatory, or marketing claims.
- The wrapper invokes upstream tools through documented entry points.
- Limitations are concrete.
