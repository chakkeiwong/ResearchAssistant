# M19 Exact Live Approval Packet Review Verdict Round 1

Date: `2026-07-14`
Reviewer: Codex read-only reviewer
Verdict: `REVISE`

The command imports the package from mutable installed `site-packages`, while
the initial preflight bound only the separate wheel archive, import origin, and
repository source hash. Same-path installed-code drift could therefore pass.

Required repair: bind the installed code actually executed, either by checking
the installed `survey/build.py` hash or by replaying the installed distribution
against the already hashed wheel. The installed bytes currently match; this is
a packet/preflight defect rather than an observed code drift.

The commit/tree/ancestor, supervisor bytes, command environment, route hash,
four requests, limits, absent root, and one-attempt boundary otherwise agree.

`VERDICT: REVISE`
