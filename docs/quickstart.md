# Quickstart

## Try The Demo

```bash
ra --root /tmp/research-assistant-demo demo setup
ra --root /tmp/research-assistant-demo demo run
ra --root /tmp/research-assistant-demo release-report
ra --root /tmp/research-assistant-demo backup create
```

The demo creates a fixture paper, a derivation worksheet, experiment evidence, a traceability report, governance/model-policy records, readiness output, and a backup archive. It uses local deterministic data only.

## Start Your Own Workspace

```bash
ra --root ~/research-assistant-workspace init
ra --root ~/research-assistant-workspace doctor
ra --root ~/research-assistant-workspace privacy status
```

Then ingest or inspect papers:

```bash
ra --root ~/research-assistant-workspace ingest --pdf ~/papers/example.pdf --query "paper title"
ra --root ~/research-assistant-workspace find --query "transport maps"
ra --root ~/research-assistant-workspace show --paper-id paper_example
```

Generated derivations, synthesis, graph reports, benchmark reports, and readiness records are review material. They do not certify mathematical correctness.

## Get Help Safely

If something fails, run diagnostics on the demo or an empty workspace first and share only non-private output. See `docs/support.md` for the support checklist and private-data boundary.
