# Industrial Release Definition

## Release Levels

### Individual Pilot

- One user, one private local workspace.
- Wheel or source checkout install.
- No shared service, shared database, SSO/RBAC, production UI, or live provider
  workflow.
- Current status: validated locally on Linux/WSL2 with Python 3.11.15.

### Departmental Beta

- Limited group trial with explicit owner and support boundary.
- Requires external validation records for target platforms and users.
- Requires publication approval, sanitized corpus rehearsal, security/ops
  checklist, and department SOP owner review.
- Shared service, SSO/RBAC, and UI may remain disabled unless their governed
  integration gates are accepted.

### Industrial Production

- Department-owned production platform with approved storage, service, identity,
  security, operations, SOPs, monitoring, incident response, backup/restore, and
  release rollback.
- Requires all industrial release gates to pass or have documented owner
  waivers.

## Trust Boundary

Generated text, parser output, benchmark output, derivation worksheets,
experiment records, traceability reports, LLM outputs, and readiness reports are
review material. They do not certify mathematical correctness, parser accuracy,
experiment reproducibility, or code correctness until a human approval workflow
accepts them.

## Current Decision

The project is currently an `individual_pilot`. Departmental beta and industrial
production remain blocked until the industrial release gate records complete
external validation, publication approval, governed integrations, security/ops
signoff, scalability evidence, and SOP approval.
