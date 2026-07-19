# M23 Terminal Fallback Review Round 3

Date: `2026-07-19`
Reviewer: fresh Codex read-only fallback
Surface: `_r7` compact terminal packet
Verdict: `REVISE`

## Material Finding

`_r7` proves offline installation and operational behavior from the current
dirty working tree, but it does not prove the master/reset claim that the
supporting implementation, tests, scripts, results, and compact evidence are
versioned and reproducible from clean `main`.

The manifest records `worktree_dirty=true`. The M23 runner, tests, result,
review records, and several M22 scientific-evidence authorities are ignored or
untracked. This fires the master program's explicit untracked-runtime and
clean-checkout veto. The wheel preserves installed package bytes, but not the
complete source/test/document/evidence state needed to regenerate the M22/M23
evidence and claimed gates from the recorded commit.

## Required Repair

1. Withdraw the active accomplished claim while the versioned close is pending.
2. Make M23 generate and replay a fresh M22 root rather than depend on an
   ignored prebuilt M22 validation root.
3. Select and commit the exact runtime, tests, scripts, plans/results/reviews,
   compact retained authorities, and exact cited technical-source members.
4. Exclude raw archive bodies, wheels, virtual environments, copied execution
   sources, logs, and unrelated generated output.
5. From a clean checkout of that commit, rerun the affected gate and fresh M23
   acceptance, then submit the clean candidate to terminal review.

`VERDICT: REVISE`
