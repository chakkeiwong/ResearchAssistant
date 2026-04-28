# Known Limitations

- This release is for private local use, not shared departmental deployment.
- Git sharing is repository/snapshot based. The tool does not provide live multi-user editing, shared database writes, SSO/RBAC, hosted UI, or server-side locking.
- Workspace merge/import is conservative: conflicts involving accepted audit facts require human resolution.
- Live LLM/provider calls are disabled by default and are not part of the individual release workflow.
- Generated derivations, experiments, synthesis, traceability, and readiness reports are review material, not mathematical approval.
- Parser quality depends on local optional tools and source/PDF quality.
- Medium-corpus performance evidence is synthetic unless a non-sensitive real corpus is explicitly recorded.
- Restore can write real files only with explicit confirmation; overwrites require an additional flag.
- Shell scripts target Linux, macOS, and WSL-style POSIX environments.
- macOS and colleague-machine onboarding remain pilot-release validation items until completed on real machines.
- Native Windows is unvalidated; use WSL for Windows colleagues.
