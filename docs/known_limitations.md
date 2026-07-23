# Known Limitations

- This release is for private local use, not shared departmental deployment.
- Git sharing is repository/snapshot based. The tool does not provide live multi-user editing, shared database writes, SSO/RBAC, hosted UI, or server-side locking.
- Workspace merge/import is conservative: conflicts involving accepted audit facts require human resolution.
- Live LLM/provider calls are disabled by default and are not part of the individual release workflow.
- New literature-survey missions are credential-free. Topic-only missions use
  bounded OpenAlex metadata nomination; explicit-seed source intake remains
  arXiv-first. Other credentialed providers remain out of scope.
- Topic-only mission identity and confirmation are implemented with a bounded
  generic OpenAlex metadata bootstrap. Provider, response, identity, and
  budget failures still stop honestly as `terminal_blocked_bootstrap_unavailable`;
  a successful bootstrap remains metadata-only candidate nomination.
- The bounded `survey central-papers` workflow autonomously nominates, attempts
  arXiv structured-source acquisition, expands OpenAlex reference/citing
  identities, constructs six audit ledgers, and assesses candidates. Its
  source-grounded classifier remains a deterministic heuristic rather than
  expert semantic judgment. The topic-input benchmark covers three reviewed
  topics; it does not establish universal recall on arbitrary topics.
- Autonomous full-text acquisition is arXiv-source-only. Publisher XML/HTML,
  lawful PDF fallback, and other repositories are not campaign providers;
  affected candidates remain source-blocked rather than treated as absent.
- Source-safety automation is limited to available OpenAlex retraction flags.
  Publisher errata, corrigenda, expressions of concern, and version conflicts
  are not comprehensively checked.
- `survey seed-papers` adds bounded OpenAlex, Crossref, and Semantic Scholar
  metadata fusion with DOI/arXiv/OpenAlex identity reconciliation. It remains
  a candidate queue: provider-local ranks, citation counts, venue fields, and
  multi-provider agreement cannot establish centrality or correctness.
- Google Scholar is not an automated provider because it has no supported
  public API. Crossref and Semantic Scholar coverage, schemas, rate limits,
  and citation metadata may be incomplete or unavailable.
- The seed-retrieval benchmark covers six evaluator-owned raw-provider cases,
  including a compound financial-recommender case with abstract evidence,
  role/facet balancing, an identity conflict, and provider gaps; it is not an
  externally curated recall estimate for arbitrary topics.
- `survey seed-papers` supports caller-supplied facets, aliases, exclusions,
  scope notes, optional venue-metric registries, and replay-validated automatic
  handoff into an explicit-seed mission. Metadata role hypotheses remain
  unverified until primary-source inspection.
- `run_seed_papers_live_smoke.py` is a bounded transport/schema diagnostic and
  requires explicit confirmation. It does not measure recall, centrality, or
  provider quality.
- The successful M22 topic case is a retained deterministic topic-selection
  replay joined to production source/omission evidence. It is not live topic-
  discovery validation.
- Forward-citation coverage is a bounded OpenAlex sample. Provider failure is
  unavailable, not zero; successful sampling is not complete citation coverage.
- M22 retains 50 identifier-bearing source-uninspected omission risks and 195
  identifier-free bibliography units with unresolved identity/count meaning.
- Qualitative assessments record merits, concerns, uncertainties, evidence
  references, and next actions. They do not authorize claim truth, prose
  readiness, completeness, publication safety, or expert consensus.
- PDF fallback is outside the active literature-survey workflow. A retained
  includepdf wrapper is reported as a technical source gap.
- Official code and publication/retraction status are not checked for all
  assessed sources.
- Generated derivations, experiments, synthesis, traceability, and readiness reports are review material, not mathematical approval.
- Parser quality depends on local optional tools and source/PDF quality.
- Parser-tool availability/degradation checks run, but parser scientific accuracy is not certified.
- Medium-corpus performance evidence is synthetic through `synthetic_git_1000` unless a non-sensitive real corpus is explicitly recorded.
- Git-sharing fixture rehearsal is synthetic and validates merge mechanics, not semantic agreement between researchers.
- macOS and native Windows are outside the supported release scope. Tagging and
  publication require explicit release-owner approval.
- Restore can write real files only with explicit confirmation; overwrites require an additional flag.
- Shell scripts target Linux and WSL-style POSIX environments.
- Linux/WSL with Python 3.11.x is the only supported release target.
- Native Windows is unvalidated; use Linux or WSL2.
- Older mission roots created under historical OpenAlex-containing discovery
  budgets are preserved evidence but are not resumed under the active arXiv-
  only contract. Start a fresh versioned mission root instead.
- Local installs may generate `*.egg-info/` metadata in the checkout. These
  files are ignored and should not be committed.
- MCP support is local stdio and read-only by default. Write-capable arXiv
  batch intake requires bounded grants and remains review material, not
  automatic approval.
- MCP is optional; absence of the MCP extra does not block the base local CLI
  workflow.
- MCP query-based arXiv discovery is not live-enabled. Bounded CLI live
  discovery can write a pinned candidate file, and planning binds the
  candidate-file checksum and exact ordered IDs into the plan hash.
- MCP PDF batch downloads are not enabled. Grant-bound CLI PDF inbox download is
  available with byte limits, duplicate/no-overwrite behavior, checksum capture,
  cleanup semantics, manifest/audit records, and one-PDF live-smoke evidence.
- Review-write is currently a CLI-only prototype. It records old/new values,
  file hashes, expiration, and audit events, but MCP review mutation remains
  disabled.
- Review-write expired proposal cleanup is CLI-only, dry-run by default, and
  removes only expired proposal records when explicitly applied.
- Deterministic mocked arXiv batch tests validate local plan/grant/run mechanics
  at 25-paper scale; live arXiv 25/50/100 public explicit-ID source intake was
  accepted on 2026-05-03. Bounded live query discovery and one-PDF live inbox
  download were also accepted on 2026-05-03, but broader PDF batch scale remains
  experimental.
- H1 external MCP setup was accepted on 2026-05-03 from an external-agent stdio
  client trial against demo data. This is optional evidence and is not a local
  external-user setup gate.
- Local MCP external/live evidence should be indexed in
  `docs/validation/local_mcp_external_validation_records.md`; absence of a
  record means the corresponding external/live claim remains unvalidated.
## Scholarly document scaffold

`ra survey literature-review --topic ...` now connects the generic central-paper
campaign to a source-attributed evidence survey candidate. It does not
automatically clear source, claim, omission, or hostile-review decisions.
Blocked candidates remain visible as omission risks, and a topic campaign may
finish with an exact open-risk status.

`ra survey draft-document` and `ra survey literature-review` use a deterministic
authority-aware synthesis baseline. They can compile LaTeX when requested, but
do not independently inspect the rendered PDF, establish literature
completeness or claim truth, or produce publication-ready prose. Topic-only
survey candidates report what checked source sections state; they do not
independently validate those statements.

DynareMCP integration is optional and limited to document structure and exact
consistency diagnostics over caller-supplied facts. A clean result does not
establish technical support, prose quality, or publication readiness.
