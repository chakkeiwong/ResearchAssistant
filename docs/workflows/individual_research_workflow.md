# Individual Research Workflow

Use this workflow for private local research notes and evidence tracking.

```bash
ra --root ~/ra-workspace init
ra --root ~/ra-workspace doctor
ra --root ~/ra-workspace ingest --pdf ~/papers/example.pdf --query "paper title"
ra --root ~/ra-workspace show --paper-id paper_example
ra --root ~/ra-workspace derivation create --paper-id paper_example --title "Main theorem worksheet"
ra --root ~/ra-workspace experiment checklists
ra --root ~/ra-workspace traceability build --paper-id paper_example
ra --root ~/ra-workspace governance build --paper-id paper_example
ra --root ~/ra-workspace industrial-readiness build --report-id local_readiness
ra --root ~/ra-workspace performance smoke --synthetic-count 25
ra --root ~/ra-workspace backup create
```

Review boundary:
- source and parser evidence are evidence, not proof;
- generated worksheets and proposals require human review;
- implementation links show traceability targets, not correctness;
- readiness reports summarize blockers and warnings, not approval.
