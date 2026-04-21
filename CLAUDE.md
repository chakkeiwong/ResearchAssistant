# CLAUDE.md

## Working style

### Think before coding
- State assumptions explicitly before implementing when they matter to the approach.
- If there are multiple reasonable interpretations, surface them instead of picking one silently.
- If a simpler approach exists, say so and prefer it unless the task requires more.
- If something is unclear, stop and name the uncertainty instead of guessing.

### Simplicity first
- Write the minimum code that solves the requested problem.
- Do not add features, abstractions, configuration, or flexibility that were not asked for.
- Do not add error handling for scenarios that cannot occur at the relevant boundary.
- If a solution feels overcomplicated, simplify it before proceeding.

### Surgical changes
- Touch only the code required for the request.
- Do not refactor, reformat, or improve adjacent code unless the task requires it.
- Match existing local style and structure.
- Remove imports, variables, and helpers made unused by your own changes.
- If you notice unrelated dead code or problems, mention them instead of changing them unprompted.
- Every changed line should trace directly to the user’s request.

### Goal-driven execution
- Turn each task into concrete success criteria that can be verified.
- For bug fixes, prefer reproducing the issue with a test or explicit check before fixing it.
- For behavior changes, verify the requested outcome directly rather than assuming the code is correct.
- For multi-step tasks, use a short plan where each step includes its verification check.
- Do not consider work done until the relevant checks pass or you have clearly reported what remains unverified.

### Comments for maintainability
- Default to clear code, but include concise explanatory comments when they help inexperienced maintainers understand non-obvious reasoning or constraints.
- Prefer comments that explain why a choice was made or what assumption matters, not line-by-line narration of what the code does.
- Do not add broad documentation blocks unless the task calls for them.
