# NeuTra DSGE Showcase Report Plan - 2026-04-29

## Motivation

The release report currently proves that the package is careful, local, and
validated, but it reads too much like release machinery. To attract colleagues,
the report needs a realistic showcase that demonstrates why a researcher would
adopt the package for daily work.

The best current showcase is a DSGE chapter-writing workflow seeded by
"NeuTra-lizing Bad Geometry in Hamiltonian Monte Carlo Using Neural Transport"
and expanded into a survey of normalizing-flow and neural-transport
architectures for difficult posterior geometry.

This example is grounded in existing project material:

- `docs/test_plan.md` already lists NeuTra as a representative paper.
- `docs/validation_run_log.md` records a NeuTra ingest validation.
- `docs/hardening_plan.md` identifies NeuTra citation-graph traversal as a
  success criterion for useful literature work.

## Scope

This is documentation/report work only. It must not change product behavior.

The showcase should describe the tool as helping a researcher:

- seed a literature workspace from NeuTra and related public papers;
- organize normalizing-flow architectures into a chapter taxonomy;
- separate DSGE-relevant posterior-sampling methods from generally related
  machine-learning papers;
- record human review notes and evidence links;
- link papers to chapter sections, code experiments, derivation notes, and
  traceability reports;
- export approved context for downstream writing.

The showcase must not claim that the tool automatically writes the survey,
certifies parser accuracy, proves mathematical correctness, or approves
research conclusions.

## Implementation Instructions

1. Update `docs/plans/reset_memo_2026-04-26.md` before and after each phase.
2. Add a substantial section to
   `proposal/research_development_assistant_design.tex` under "Nontrivial
   Showcases".
3. Include practical command examples using existing commands:
   - `ra ingest`
   - `ra citation-neighborhood`
   - `ra audit-note`
   - `ra link-add`
   - `ra derivation create`
   - `ra synthesis propose`
   - `ra traceability build`
   - `ra export-context`
4. Add a concise pointer in `docs/usage.md` so users see the use case outside
   the PDF.
5. Strengthen docs smoke assertions in
   `tests/integration/test_individual_release_cli.py` for the showcase terms.
6. Rebuild `proposal/research_development_assistant_design.pdf` if `pdflatex`
   is available.
7. Remove TeX intermediates and avoid committing generated/private local state.

## Validation

Run:

```bash
PYTHONPATH=src timeout 180 python -m pytest tests/integration/test_individual_release_cli.py -q
git diff --check
```

If the PDF is rebuilt, run two passes from `proposal/`:

```bash
timeout 180 pdflatex -interaction=nonstopmode -halt-on-error research_development_assistant_design.tex
timeout 180 pdflatex -interaction=nonstopmode -halt-on-error research_development_assistant_design.tex
```

## Acceptance Criteria

- The report contains a realistic NeuTra/DSGE normalizing-flow survey showcase.
- The showcase is motivating but honest about human review and limitations.
- The release target remains individual local filesystem plus Git sharing.
- The PDF is rebuilt or the inability to rebuild is recorded.
- Focused docs tests pass.
- Reset memo records the evidence and remaining blockers.
