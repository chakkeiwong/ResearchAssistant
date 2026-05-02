# MCP Review-Write Design Gate

Review mutation is intentionally deferred from the first local MCP addition.

## Why Deferred

Changing review state is a trust-bearing action. Marking a paper approved,
rejecting a record, appending technical-audit notes, or accepting inbox items
can change how later writing and coding workflows interpret evidence.

The current MCP implementation supports:

- read-only local inspection;
- plan-first arXiv batch intake;
- grant-bound source-fetch execution that creates review material only.

It does not expose review mutation tools.

## Future Permission Mode

A future `review_write` mode should be separate from `arxiv_batch_intake`.

It should allow only a narrow list of operations:

- mark review status;
- append audit note;
- set audit note;
- remove audit note;
- accept/reject inbox proposal.

## Required Confirmation Payload

Every future review-write action should bind confirmation to:

- workspace root;
- paper ID or inbox proposal ID;
- operation;
- old value;
- new value;
- exact file path to change;
- expected file hash or version;
- risks;
- confirmation ID;
- expiration time.

Do not use a generic `confirm=true` flag.

## Required Audit Event

Each applied review-write action should record:

- actor/source as local MCP;
- tool name;
- grant or confirmation ID;
- old value;
- new value;
- file path;
- previous hash;
- new hash;
- timestamp;
- whether the action requires later human review.

## Conflict Behavior

If the file changed after the proposal was created, the write must block and
return a conflict payload. The assistant should ask the human to inspect the
new state rather than overwriting it.

## Out Of Scope

- bulk review approval;
- silent promotion of generated/parser content;
- destructive correction;
- automatic mathematical approval;
- review writes through hosted/shared MCP.
