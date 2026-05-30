# Versioning Policy

This is MVP scaffolding, not a released package API.

Allowed without migration:

- new manifest keys
- new evidence-pack fields
- new opt-in gates
- new verifier specs

Needs an explicit migration plan:

- renaming/removing eval_engine-read manifest fields
- renaming evidence-pack files
- changing a gate's pass/fail semantics for existing manifests

Schema updates should be additive unless they fix a field that was never meant
to be public.

## Evidence-pack format version

Every pack carries `pack_format_version` in `manifest.json`. Current value:
`1.0.0`. The source of truth is `eval_engine.common.PACK_FORMAT_VERSION`; the
descriptor at `spec/evidence_pack.schema.json` lists which versions a
contract-aware reader accepts.

- Additive (minor/patch bump): new optional pack files, new optional fields,
  new gate status values. Existing readers must continue to pass.
- Breaking (major bump): removing or renaming pack files, removing required
  fields, changing the meaning of an existing field or status value, or
  tightening a previously-loose constraint. Requires a migration note and an
  entry added to `supported_pack_format_versions`.
- Verifiers that consume packs should declare which pack versions they accept
  and refuse to over-claim on unsupported versions.
