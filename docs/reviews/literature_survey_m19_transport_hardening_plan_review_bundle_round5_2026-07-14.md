# M19 Transport Hardening Plan Review Bundle, Round 5

Date: `2026-07-14`
Reviewer role: passive read-only

Review only the final-evidence harness repair in
`docs/plans/literature_survey_north_star_m19_metadata_transport_hardening_subplan_2026-07-14.md`.

Observed evidence: final attempt 02 used
`docs/validation/.../pytest_tmp/full_cli` as pytest basetemp. The full CLI suite
then had `124 passed, 1 failed`; the only failure was
`test_cli_surveybench_run_success_and_output_file`, which expects an output
path outside the repository to serialize as `redacted:<name>`, but the in-repo
basetemp correctly serialized as a repository-relative path. Earlier
diagnostic full CLI with external pytest temp passed `125/125`.

Repair: keep JUnit/log in the exact final evidence root; keep in-root basetemps
for transport, supervisor, affected Phase 7, and cumulative M16/M17; use only
the exact absent external basetemp
`/tmp/ra_m19_full_cli_basetemp_attempt03/` for full CLI. It is retained for
audit, never copied into or hashed as final evidence, and does not change test
selection or product code. The final evidence root remains absent once then
append-only, with every gate target/basetemp individually absent before use.

Decide whether this repairs the wrong-baseline harness without weakening test
or artifact evidence. Do not run commands, tests, Python, helpers, network,
GPU, Git mutation, or external models. Do not edit. Return findings and exactly
`VERDICT: AGREE` or `VERDICT: REVISE`.
