# Proposal: Cross-Platform Research Development Assistant for Quantitative Policy and Finance Engineering

## Executive Summary

This proposal recommends building a **shared, code-aware research development assistant** for the division's economists, mathematical-finance researchers, and policy-model developers. The system is designed to bridge the current gap between:

- paper-centric research tools such as SciSpace,
- code-centric assistants such as Claude Code, Copilot, and Cursor,
- and the actual needs of research-engineering workflows in large institutions.

The core idea is to build a **local-first research intelligence layer** that sits underneath all three coding assistants rather than attempting to replace them. The system will provide:

1. structured paper ingestion and metadata management,
2. code-aware research memory,
3. equation-to-code and paper-to-code traceability,
4. reviewer-facing literature synthesis,
5. executable technical documentation support,
6. shared retrieval interfaces usable across Claude Code, Copilot, and Cursor.

The recommended architecture is **tool-agnostic and interface-driven**:
- a local or team-hosted backend for paper ingestion, indexing, and structured summaries,
- a common data model stored in inspectable files or a lightweight database,
- adapter layers for Claude Code, Cursor, and Copilot,
- and optional MCP support where available.

This proposal argues that such a system is both **technically feasible** and **strategically valuable** for a group of approximately 50 research-oriented developers working on mathematically sophisticated, code-heavy institutional models.

---

## 1. Problem Statement

### 1.1 Current workflow deficiency

The division's current workflow relies on a fragmented combination of:
- PDF and citation tools for reading papers,
- AI coding assistants for writing and editing code,
- manually maintained notes for research conclusions,
- and ad hoc copying/pasting across tools.

This creates several persistent problems:

1. **Paper tools are not code-aware.**
   They can summarize papers and answer questions about text, but they do not understand how a method relates to the repository, implementation status, testing, numerical issues, or production constraints.

2. **Coding assistants are not research-memory aware enough.**
   They may reason well within a single interaction, but without a structured research layer they repeatedly miss context, lose code-literature links, and require the user to restate information that should already be available.

3. **Review-quality technical writing is too manual.**
   Researchers spend too much time correcting trivial wording errors, restoring missing context, verifying whether citations actually support claims, and connecting equations to implementation.

4. **There is no shared research-development memory.**
   Knowledge is distributed across personal notes, PDFs, code comments, and partially documented conversations. This is manageable for one researcher but not for a group of 50.

5. **Skeptical review is hard to support.**
   For institutional quantitative work, review often demands exact traceability:
   - what paper supports this claim?
   - what are the assumptions?
   - what code implements this method?
   - what experiments tested it?

The current workflow does not make those links easy to maintain.

### 1.2 Why this matters specifically for our field

This problem is especially severe in mathematical finance, DSGE modeling, macro-finance, and structural estimation because the work combines:
- mathematical derivation,
- econometric assumptions,
- numerical methods,
- software engineering,
- simulation and empirical validation,
- and reviewer-facing technical writing.

Most existing tools are optimized for only one part of this stack.

---

## 2. Goal of the Proposed Tool

The proposed system should become a **shared research development layer** for the division.

It is not intended to replace Claude Code, Copilot, or Cursor. Instead, it should make all three more useful by giving them access to the same structured research and implementation context.

The primary goals are:

1. **Reduce repetition and context loss** across tools.
2. **Connect literature to code and documentation** in a durable, inspectable way.
3. **Improve technical writing quality** for reviewer-facing outputs.
4. **Support research-oriented software development** rather than generic software development.
5. **Work across multiple assistants** already used by the division.
6. **Remain transparent and auditable** enough for serious institutional use.

---

## 3. Core Design Principles

The system should be built around the following principles.

### 3.1 Tool-agnostic, not assistant-specific

Because the division uses Claude Code, Copilot, and Cursor, the system cannot depend exclusively on a single assistant's proprietary interaction model.

The right design is:
- one shared research backend,
- multiple front-end integrations.

### 3.2 Local-first and inspectable

Researchers must be able to inspect, edit, version-control, and repair the data manually.

For this reason, the system should prefer:
- plain files where possible,
- explicit schemas,
- reproducible extraction and summary pipelines,
- and auditable metadata.

### 3.3 Research-memory aware

The tool should preserve not only paper metadata, but also:
- what the paper contributes,
- what assumptions it makes,
- what criticisms are relevant,
- whether it is implementable,
- where it connects to the codebase,
- and how it affects current design decisions.

### 3.4 Reviewer-oriented

The system should be built not just for convenience, but for producing outputs that can survive skeptical external or internal review.

### 3.5 Incremental and practical

The first useful version should not attempt to solve every problem. It should focus on the core workflow:
- ingest papers,
- summarize them structurally,
- link them to code and documents,
- expose that context to coding assistants.

---

## 4. High-Level Architecture

## 4.1 Overview

The recommended architecture has four layers:

1. **Paper Ingestion Layer**
2. **Structured Research Store**
3. **Query / Retrieval Layer**
4. **Assistant Integration Layer**

### 4.1.1 Paper Ingestion Layer

Responsibilities:
- import PDF, DOI, arXiv, and URL sources,
- extract metadata,
- extract text,
- identify references and citations where possible,
- generate structured summaries.

Possible components:
- `pdftotext` / PDF extraction,
- OpenAlex, Crossref, arXiv APIs,
- optional OCR for scanned PDFs,
- text cleaning and chunking logic.

### 4.1.2 Structured Research Store

The research store should hold:
- paper metadata,
- extracted text,
- curated summaries,
- literature relationships,
- code links,
- document links,
- reviewer notes,
- and implementation judgments.

This can be file-based initially, possibly with a lightweight database index later.

### 4.1.3 Query / Retrieval Layer

This layer exposes reusable operations such as:
- find a paper,
- list citing papers,
- read a structured summary,
- find papers related to a topic,
- list code files linked to a paper,
- find all papers relevant to a method family,
- produce reviewer-facing synthesis.

This is the shared intelligence layer.

### 4.1.4 Assistant Integration Layer

Each coding assistant can interact with the same underlying system through different adapters.

Possible integration modes:
- MCP where available,
- local CLI tools,
- indexed note files in the workspace,
- editor plugins or extension commands,
- local HTTP API.

This is the key to tool portability.

---

## 5. Why a Shared Backend is the Right Cross-Platform Strategy

The requirement that the tool must work with Claude Code, Copilot, and Cursor rules out a design that is deeply entangled with only one of them.

The most robust way to satisfy the requirement is:

### Build once, integrate many times.

That means:
- all paper intelligence lives in one backend,
- all assistant-specific behavior is just an adapter.

This is feasible because the truly valuable components are independent of the front-end assistant:
- paper ingestion,
- metadata resolution,
- structured summaries,
- code-literature linking,
- and research retrieval.

These do not inherently belong to Claude, Cursor, or Copilot.

This is also strategically superior because the division can change assistant usage later without losing the research layer.

---

## 6. Functional Requirements

The system should support the following use cases.

### 6.1 Literature ingestion
- import a paper from PDF / DOI / arXiv / URL,
- extract metadata,
- store raw PDF,
- store extracted text,
- detect if it is already in the library.

### 6.2 Structured paper summary
For each paper, store fields such as:
- title,
- authors,
- year,
- DOI/arXiv/URL,
- abstract,
- main method,
- assumptions,
- strengths,
- limitations,
- exactness/correction mechanism,
- relevance to current project,
- code implications,
- reviewer concerns,
- related papers,
- linked code files,
- linked monograph/document sections.

### 6.3 Citation and related-work queries
- papers citing X,
- papers cited by X,
- related methods,
- neighboring literature,
- criticisms and remedies.

### 6.4 Code-aware linking
The system should allow explicit links such as:
- paper ↔ code file,
- paper ↔ method class,
- paper ↔ monograph section,
- equation ↔ implementation file,
- criticism ↔ mitigation in code.

### 6.5 Reviewer-facing synthesis
The tool should support generation of outputs such as:
- literature review sections,
- skepticism / objection sections,
- implementation feasibility assessments,
- code-linked technical documentation,
- audit notes showing which paper supports which claim.

### 6.6 Shared team usage
The tool should support:
- shared schemas,
- shared paper stores,
- per-user notes layered on top,
- project-specific research collections,
- team-wide conventions.

---

## 7. Proposed Data Model

The first implementation should use a file-first design.

### 7.1 Suggested directory structure

```text
research/
  papers/
    raw/
    extracted/
  metadata/
  summaries/
  links/
  reviews/
  schemas/
```

### 7.2 Example paper summary schema

Each paper could have a structured YAML or JSON document with fields like:

- `id`
- `title`
- `authors`
- `year`
- `doi`
- `arxiv_id`
- `source_url`
- `abstract`
- `method_family`
- `main_contribution`
- `mathematical_core`
- `exactness_status`
- `invertibility_mechanism`
- `jacobian_handling`
- `known_defects`
- `known_remedies`
- `scientific_relevance`
- `dsge_relevance`
- `linked_files`
- `linked_docs`
- `reviewer_notes`
- `status`

This structure is simple enough to maintain but rich enough to drive useful retrieval.

---

## 8. Integration Strategy Across Claude Code, Copilot, and Cursor

## 8.1 Claude Code

Claude Code can interact well with:
- local files,
- CLI commands,
- MCP tools.

This makes Claude Code the easiest first-class integration target.

## 8.2 Cursor

Cursor can benefit from:
- workspace-visible structured files,
- local helper scripts,
- MCP if available,
- explicit context files and research summaries.

## 8.3 Copilot

Copilot is the least naturally suited to deep research workflows, but it can still benefit through:
- well-structured local research files,
- generated documentation in the workspace,
- code comments linked to literature,
- local helper commands outside the assistant itself.

This means the backend still helps Copilot users, even if the interaction quality is not as rich as Claude Code.

## 8.4 Recommended cross-platform design

Support multiple access paths:
1. **MCP server** for tools that support it,
2. **CLI commands** for general tool portability,
3. **workspace research files** for assistant-agnostic visibility,
4. optionally later a **small local HTTP API**.

This gives the division resilience across assistants.

---

## 9. Why This is Feasible for Our Group

This project is feasible because the first version does not require building a large enterprise software platform.

A useful version 1 only requires:
- a disciplined file structure,
- metadata extraction scripts,
- summary-generation and validation workflow,
- a small query layer,
- and integrations that expose this to assistants.

This is a manageable engineering effort, especially if developed iteratively.

The group's domain expertise is actually a major advantage:
- the team knows what questions matter,
- what skeptical review looks like,
- which methods recur,
- and what code-literature traceability is needed.

The main requirement is to avoid overbuilding too early.

---

## 10. Major Risks and Mitigations

### Risk 1: Over-engineering too early
**Mitigation:** Start file-first and local-first. Delay fancy UI and platform features.

### Risk 2: Poor paper extraction quality
**Mitigation:** Keep raw PDF, extracted text, and curated summaries separate.

### Risk 3: Hallucinated literature links or overconfident summaries
**Mitigation:** Use structured fields, citation validation, and reviewer notes. Mark uncertainty explicitly.

### Risk 4: Tool fragmentation across assistants
**Mitigation:** Centralize logic in the backend and expose multiple access paths.

### Risk 5: Low team adoption
**Mitigation:** Start with painful workflows people already experience:
- literature review generation,
- paper-to-code traceability,
- reviewer-facing documentation.

---

## 11. Recommended Implementation Roadmap

### Phase 1: Minimal viable research backend
- local paper library,
- metadata retrieval,
- PDF extraction,
- structured paper summaries,
- manual link files.

### Phase 2: Query layer and assistant integration
- local CLI tools,
- MCP interface for Claude Code and possibly Cursor,
- simple assistant-friendly retrieval commands.

### Phase 3: Code-aware research workflows
- equation-to-code links,
- paper-to-file links,
- document traceability,
- reviewer-facing report generation.

### Phase 4: Group adoption features
- shared conventions,
- project templates,
- optional team-hosted index,
- optional lightweight UI.

---

## 12. Recommended MVP Scope

The MVP should do exactly these things well:

1. ingest papers,
2. extract metadata and text,
3. create structured summaries,
4. link papers to code and documents,
5. answer literature queries from coding assistants,
6. support reviewer-facing synthesis.

That is enough to create substantial value without becoming an unbounded engineering effort.

---

## 13. Why This Would Be Valuable for the Division

This tool would directly improve:
- speed of literature-informed coding,
- quality of technical documentation,
- consistency of reviewer-facing arguments,
- onboarding of researchers with less engineering background,
- maintainability of mathematically sophisticated production code,
- and continuity of knowledge across projects and staff.

It is especially well matched to a division composed of academics turned engineers, because it addresses exactly the gap between paper-based reasoning and institutional-grade software work.

---

## 14. Recommendation

Proceed with a phased build of a **shared, assistant-agnostic research development backend** for the division.

The proposed system is:
- technically feasible,
- strategically differentiated,
- valuable even in a minimal version,
- and compatible with Claude Code, Cursor, and Copilot through a backend-plus-adapter approach.

The strongest recommendation is to begin with a local-first MVP focused on:
- literature ingestion,
- structured research memory,
- code-aware linking,
- and assistant-facing retrieval.

This is the most practical path to delivering a useful tool for the whole group without taking on unnecessary platform complexity too early.
