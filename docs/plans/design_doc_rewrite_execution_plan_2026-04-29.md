# Research Development Assistant Design Rewrite Execution Plan - 2026-04-29

## Purpose

This plan governs a substantial rewrite of `proposal/research_development_assistant_design.tex` so the document is strong enough to send to technically skeptical colleagues as an adoption-oriented package proposal.

The current file is already closer to the real release than the older broad platform draft, but it still reads primarily as a release report/manual. The goal of this plan is to reshape it into a more readable, more appealing, more persuasive document with better exposition and stronger examples, while preserving factual accuracy about the current release.

## Release Scope That Must Remain True

The rewrite must stay faithful to the bounded v0.1 release already documented in the repository:

- one individual local researcher first;
- local filesystem storage;
- offline/provider-disabled default workflows;
- Git-based sharing by repository exchange and explicit merge/import;
- no current shared backend, shared database, hosted UI, SSO/RBAC, or real-time collaboration;
- parser/generated/benchmark/derivation/traceability/readiness outputs remain review material, not accepted scientific conclusions.

The document may discuss future extensions, but it must not present them as current capabilities or near-term guarantees.

## Primary Problem To Solve

The current `proposal/research_development_assistant_design.tex` has solid technical substance, but it is not yet optimized for colleague persuasion:

- it foregrounds release/manual/report material rather than colleague adoption;
- it does not lead with the strongest day-one user stories;
- it underuses the clearest product language already present in `README.md`, `docs/usage.md`, and `docs/workflows/individual_research_workflow.md`;
- it needs a more deliberate narrative sequence from pain point to practical value to bounded technical credibility.

## Non-Negotiable Rules

- Do not overclaim capabilities beyond the current repo state.
- Do not reintroduce the old broad hosted/shared-platform framing as the main story.
- Do not present generated artifacts as scientific approval or proof.
- Do not fake fresh-reader, macOS, minimal-machine, tag, or publication evidence.
- Do not weaken existing privacy/trust-boundary language.
- Do not add examples that imply private corpora, credentials, or non-shareable local data.
- Keep command examples aligned with real current CLI commands.
- Ensure the final `.tex` file still compiles.
- Do not let derivation, experiment, synthesis, traceability, governance, or readiness scaffolds displace ingest/review/export as the core colleague adoption story.

## Reference Sources To Reuse

### Normative truth sources

These files define the package posture the rewrite must not contradict:

- `README.md`
- `docs/usage.md`
- `docs/product_spec.md`
- `docs/known_limitations.md`
- `docs/workflows/individual_research_workflow.md`

### Supplementary style and example sources

These files may be reused for wording or examples when they remain consistent
with the normative sources:

- `docs/installation.md`
- `docs/quickstart.md`
- `docs/support.md`
- `docs/release_notes_0.1.0.md`

## Required Independent Audit Before Execution

Before editing the LaTeX file, another-developer review of this plan must check:

1. **Scope fidelity**
   - The plan keeps the document centered on the actual current local release.
2. **Persuasion quality**
   - The plan genuinely improves readability and colleague appeal rather than only shortening or reorganizing.
3. **Example strategy**
   - The proposed examples are realistic, current, and persuasive.
4. **Truthfulness**
   - The rewrite will not blur pilot limitations or manual release blockers.
5. **Document design**
   - The structure supports a colleague reading for adoption, not just a maintainer reading for release details.
6. **Safety/privacy**
   - Proposed examples and screenshots/snippets do not encourage exposing private local data.
7. **Verification rigor**
   - The plan includes command checks, claim checks, and intermediate compile checks.

If the audit finds missing points, update this plan before execution and record the audit in `docs/plans/reset_memo_2026-04-26.md`.

## Execution Loop For Every Phase

For every phase below, follow this exact cycle:

1. Plan the smallest safe change for the phase.
2. Execute the phase.
3. Run focused validation.
4. Audit the result as another developer.
5. Tidy generated outputs and avoid staging private/generated files.
6. Update `docs/plans/reset_memo_2026-04-26.md` with phase evidence, result, and next step.

## Phase 0 - Baseline, Rewrite Boundary, And Current-Document Inventory

### Goal

Establish the rewrite boundary and map the current document so no important trust-boundary content is lost and no low-value operational material is accidentally retained.

### Actions

- Re-read the current `proposal/research_development_assistant_design.tex`.
- Re-read the normative truth-source documents listed above.
- Build a section-by-section keep/cut/move/compress inventory for the current proposal:
  - keep with rewrite;
  - compress;
  - move later or appendix;
  - remove.
- Record the rewrite boundary in the reset memo:
  - the package remains individual/local/private/offline-default;
  - examples must use real commands;
  - future multi-user/platform work must be demoted to explicit future scope;
  - trust-boundary caveats must remain visible;
  - the document must persuade colleagues to try the package now.

### Tests

- no code tests required for this phase;
- verify the memo update is internally consistent and cites the correct files;
- verify every current major proposal section has been explicitly mapped to keep/compress/move/remove.

### Acceptance criteria

- rewrite boundaries are explicit;
- every current major proposal section has a disposition;
- no editing of the proposal body begins before the boundaries and inventory are recorded.

## Phase 1 - Rewrite The Narrative Structure

### Goal

Replace the current report/manual-first flow with a colleague-facing adoption narrative.

### Actions

Restructure `proposal/research_development_assistant_design.tex` around this sequence:

1. Executive summary
2. The concrete workflow problem
3. What the package does in the current release
4. Why local-first is the right design
5. How it fits into current assistant workflows
6. Concrete example workflows
7. Scope boundaries and non-goals
8. Technical credibility and implementation summary
9. Adoption path / pilot path
10. Skeptical questions and answers
11. Future extensions
12. Appendix-style operational or release details if still needed

Future-platform material must not appear in the title, executive summary, opening
chapters, or first workflow example except as explicit non-goal or future scope.

### Tests

- verify section order and headings in the `.tex` source;
- verify maintainer/release-gate material no longer appears before the first concrete workflow example;
- run an intermediate compile check after the structural rewrite.

### Acceptance criteria

- the document has the new top-level narrative structure;
- the opening structure no longer reads primarily like a release checklist;
- the document still compiles after the structural rewrite.

## Phase 2 - Rewrite The Opening Pages For Persuasion

### Goal

Make the first pages strong enough that a colleague quickly understands why the package is worth trying.

### Actions

Rewrite the title, opening framing, executive summary, and first chapters so they:

- state the current release scope clearly;
- lead with the practical workflow problem;
- explain the value proposition in plain but technically serious language;
- describe why the tool is useful without claiming it automates judgment.

The title/subtitle must stop foregrounding release review or future-extension
planning and instead foreground bounded current package value for colleagues.

### Tests

- compare the first pages against `README.md`, `docs/product_spec.md`, and `docs/known_limitations.md` for scope alignment;
- audit for any reintroduced hosted/platform overclaim;
- run an intermediate compile check after the opening rewrite.

### Acceptance criteria

- the first two pages explicitly state: one researcher first, local filesystem, Git-based sharing, provider-disabled/offline-default posture, and review-material trust boundary;
- title/subtitle no longer foreground release-review/manual framing;
- the opening pages are readable, accurate, and persuasive to a skeptical peer;
- the document still compiles after this phase.

## Phase 3 - Replace Weak Examples With Better Exposition And Stronger Workflows

### Goal

Center the document on realistic day-one value.

### Actions

Add or rewrite 2–3 strong examples using current real commands and current product posture, likely including:

1. ingest a paper and inspect the structured local summary;
2. discover related work / citation neighborhood and export trusted context for writing or coding;
3. connect a paper to future chapter/code work as durable research memory.

The examples should:

- be short and readable;
- explain the pain point before the command sequence;
- explain why the output is useful;
- preserve uncertainty and review-boundary language.

Use only public papers, generic placeholders, or temp/local-safe paths such as
`/tmp/...` or `~/ra-workspace`. Do not use personal corpora paths. When showing
export, prefer reviewed subsets such as `ra export-context --review-status approved ...`.

### Tests

- build a command-verification checklist mapping each command retained in the proposal to a current source in `README.md`, `docs/usage.md`, or `docs/workflows/individual_research_workflow.md`;
- verify commands shown are real current commands from docs/CLI;
- audit examples for scope truthfulness and privacy safety;
- run an intermediate compile check after example rewrites.

### Acceptance criteria

- the document contains exactly 2–3 primary colleague-facing examples;
- every primary example uses real current commands verified against current docs;
- every primary example explains output value and includes an explicit review-boundary cue;
- examples are more compelling than the existing manual/report-heavy sections;
- the document still compiles after this phase.

## Phase 4 - Compress Or Demote Material That Hurts Adoption

### Goal

Reduce content that is accurate but weakens persuasion when placed too prominently.

### Actions

Substantially compress, move later, or demote:

- overly operational release-checklist material;
- sections that read mainly as maintainer notes rather than colleague value;
- duplicated or low-value future-platform detail;
- any remaining broad platform rhetoric that is not necessary to explain the current package;
- excessive implementation density that interrupts the main narrative.

Keep enough technical detail to preserve credibility.

### Tests

- audit for missing important trust-boundary or scope information after compression;
- ensure the resulting document still explains what is actually built;
- verify that maintainer/release-ops content remaining in the main narrative is intentionally justified and brief.

### Acceptance criteria

- the main body contains no more than one concise release-validation/adoption-path section;
- maintainer-only notes are moved later, reduced, or removed;
- the document is tighter and more appealing without becoming vague or inaccurate.

## Phase 5 - Add A Bounded Technical Credibility Section

### Goal

Keep the document rigorous enough for technically demanding colleagues.

### Actions

Retain a concise section explaining:

- structured local artifacts and provenance;
- source-first arXiv audit posture;
- parser capability limits and review boundaries;
- why the package complements coding assistants instead of replacing them;
- why local inspectability is a strength.

This section should reassure technical readers without reverting to a monograph.

### Tests

- compare against `README.md`, `docs/usage.md`, `docs/product_spec.md`, and `docs/known_limitations.md` for consistency;
- run a package-promise audit covering:
  - structured-source-first for arXiv papers;
  - conservative-by-default posture;
  - provenance/review-status clarity;
  - visible degradation for remote enrichment;
  - no silent final moves for downloaded papers.

### Acceptance criteria

- the technical credibility section explicitly mentions source-first posture, parser limits, provenance, and human approval boundary;
- the document remains technically credible while still easy to read.

## Phase 6 - Final Readability Pass, Claim Audit, And LaTeX Cleanup

### Goal

Improve polish, flow, compile safety, and truthfulness.

### Actions

Perform a final pass for:

- shorter paragraphs and stronger topic sentences;
- cleaner list formatting;
- better heading wording;
- removal of stale or repeated phrasing;
- LaTeX formatting issues that harm readability.

Run a claim-audit matrix against the normative truth sources for:

- target user;
- storage model;
- sharing model;
- provider/LLM default posture;
- parser trust posture;
- generated artifact trust posture;
- release maturity/manual gates;
- OS/platform posture.

### Tests

- inspect the `.tex` for obvious structural errors;
- ensure section references and environments remain coherent;
- run an intermediate compile check after cleanup.

### Acceptance criteria

- the source is materially cleaner and easier to maintain;
- the rewritten proposal does not contradict the normative package posture;
- the document still compiles after cleanup.

## Phase 7 - Compile Validation And PDF Inspection

### Goal

Ensure the final document actually builds and renders acceptably.

### Actions

- Run a LaTeX build for `proposal/research_development_assistant_design.tex`.
- If the first build reports missing references or requires a rerun, rerun as needed.
- Inspect the result for formatting degradation.

### Tests

- successful LaTeX/PDF build;
- no fatal errors;
- no obviously broken structure in the resulting PDF;
- inspect at least:
  - title/subtitle accuracy;
  - table-of-contents order;
  - first two pages for persuasion and scope fidelity;
  - one example section for readable command listings;
  - limitations/future-scope placement.

### Acceptance criteria

- the final `.tex` compiles successfully;
- the rendered PDF passes the inspection checklist.

## Phase 8 - Final Audit, Tidy, Reset Memo, And Commit

### Goal

Finish the rewrite with a clean audit trail and the user-requested commit.

### Actions

- Audit the final document as another developer:
  - would a colleague want to try this package after reading it?
  - does the document stay within the real current release scope?
  - are limitations stated honestly?
  - are examples strong and realistic?
- Tidy generated build outputs if needed.
- Update `docs/plans/reset_memo_2026-04-26.md` with phase completion, build evidence, and final status.
- Review the diff.
- Create the requested git commit with only intentional files.

### Tests

- `git diff --check`
- final `git status --short`
- compile evidence recorded in the memo

### Acceptance criteria

- the rewrite is complete, audited, compiled, documented, and committed.

## Resumed Independent Audit - 2026-04-29

### Audit posture

This plan was re-audited from the standpoint of another developer before the
remaining execution work resumed. The audit treated the already-completed
Phases 0 through 6 as implementation evidence and focused on whether the plan
still contains enough instruction to finish without human intervention.

### Findings

- Scope fidelity is adequate. The plan repeatedly anchors the report to the
  individual local filesystem release and keeps hosted multi-user work as
  future scope.
- The execution loop is explicit enough for autonomous work: each phase requires
  planning, execution, focused validation, another-developer audit, tidy-up, and
  reset-memo evidence.
- The example strategy is sufficiently bounded because it requires current CLI
  commands, privacy-safe paths, and review-boundary language.
- Truthfulness controls are present. The plan forbids fake onboarding, macOS,
  minimal parser-machine, tag, and publication evidence.
- Verification coverage is adequate for a documentation rewrite. The remaining
  high-risk checks are LaTeX build validation, rendered-PDF inspection, and
  final diff hygiene.
- One operational point needed to be made explicit for the resumed execution:
  if the LaTeX build updates the tracked PDF, the PDF must be reviewed and
  committed with the source and reset memo. If the build output only changes
  temporary auxiliary files, those files must stay out of the repository.

### Audit conclusion

No blocking plan defects remain. The plan is executable as written for the
remaining phases. The resumed work should finish Phase 7 and Phase 8, update the
reset memo with evidence, and commit only intentional tracked release files plus
this audited plan if it is staged intentionally.
