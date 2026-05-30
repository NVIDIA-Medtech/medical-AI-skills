# Agent Skill Readiness

No-network maintainer status for the active agent-skill quality goal.

The tool combines:

- `runs/skill_audit/_summary.json` from `make verify-skills`.
- Derived lifecycle counts from the same skill audit, so agents can see how many
  targets are `published`, `verified`, `gated`, `runnable`, or `draft`.
- The no-network with-vs-without approval packet.
- The with-vs-without harness tests through the Make targets below.

It reports whether the repo is:

- locally ready for external study approval,
- already complete, or
- not ready because a local gate failed.

When the with-vs-without gate is ready for approval, the status includes the
reviewed payload fingerprint that binds the pending external reruns to the
prompt hashes, selected documentation hashes, staged inputs, backends, arms,
and repeat records in the approval packet.
It also reports direct remediation coverage, so the top-level status shows how
many pending skill/mode groups have matching external rerun commands.
The lifecycle section is intentionally high-level: use it to choose the next
review target, then open the target's `runs/skill_audit/<name>/output.json` or
run `make audit-skill SKILL=<name>` for the specific gaps. User-facing
capabilities need trusted-run verifier coverage to move past `gated`; verifier
targets need their own curated passing evidence pack and do not need
`paired_verifiers[]`.
The report includes only the first few lifecycle blockers, prioritizing
publishable skills before verifier specs, so it stays readable during broad
catalog work.

Run:

```bash
make status-agent-skills
```

Strict proof gate:

```bash
make prove-agent-skills
```

`prove-agent-skills` exits nonzero until the strict skill audit and
with-vs-without harness tests pass, the study artifacts are complete, and every
covered skill supports the SKILL.md paired advantage.
