# Benchmark Corpus Plan

## Goal

This benchmark corpus exists to stabilize parser and metadata behavior for the research assistant.

We need benchmark artifacts with known ground truth so that parser development stops depending on one-off manual debugging.

## Benchmark classes

### 1. Synthetic LaTeX benchmarks
Use self-authored LaTeX source so that title, authors, abstract, sections, equations, and references are known exactly.

### 2. arXiv source-based benchmarks
Where available, use arXiv papers with both source and PDF so that we can compare parser output against source-derived ground truth.

### 3. Real-world acceptance cases
Use a small number of local papers only for manual acceptance testing, not deterministic unit tests.

## Why arXiv source helps

Yes, many arXiv papers provide LaTeX sources. That is extremely valuable because:
- the source gives a near-ground-truth title, author list, abstract, and section structure;
- the PDF gives the real parser target;
- discrepancies between parser output and source can be measured systematically.

This is much stronger than relying only on PDF text extraction or metadata APIs.

## Recommended benchmark growth order

1. Start with a few synthetic LaTeX fixtures.
2. Add a few arXiv source/PDF pairs for transport and HMC papers.
3. Use those to evaluate parser output quality.
4. Keep real-world library papers for manual validation only.

## Current benchmark status

Currently present:
- synthetic benchmark: simple transport paper with a compiled PDF fixture
- synthetic benchmark: long title / subtitle paper with a compiled PDF fixture
- synthetic benchmark: author-footnote paper with a compiled PDF fixture
- parser benchmark scoring harness that preserves expected-record-only rows when PDFs are absent and scores parser outputs when PDFs are present

Still missing:
- arXiv source/PDF benchmark pairs
