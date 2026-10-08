# Cash Flows, Macroeconomic Scenarios, and FX Hedging

Version 2, 9 October 2026. A detailed literature survey and phased product proposal for a commercial bank with one million clients, 36 monthly observations, and incomplete visibility into each client's banking relationships.

- [Read the compiled proposal](salespitch_cashflow_fx.pdf).
- [Main LaTeX source](salespitch_cashflow_fx.tex) and [bibliography](references.bib).
- [Download the complete LaTeX source bundle](latex_sources.zip).
- [Local collection of all 12 cited papers](../../dcos/papers/salespitch/README-v2.md), with exact versions, source URLs, checksums, and technical reading anchors in [the manifest](../../dcos/papers/salespitch/manifest-v2.json).
- [Mathematical checks](review/mathematical_checks.json), [document checks](review/document_checks.json), and [terminal review](review/review_result.md).

The proposal develops a pooled dynamic model of currency-specific gross receipts and payments, an explicit macroeconomic scenario channel, and an independent FX-hedge utility and discrete-choice module. It derives the relevant filtering, smoothing, estimation, scenario-response, hedging, choice, and outreach equations. Each cited method is explained where it enters the financial argument. This is a selective methodological survey; the source chapter and omission register describe its scope.

Positive GDP responses are explicit modeling restrictions. Causal interpretations additionally require identification and invariance assumptions. The bank's observed flows do not identify total client cash flow or other-bank hedge positions. These distinctions are carried into the proposed product and phased validation, rather than resolved by assumption without disclosure.

## Build

From this directory:

```sh
bash build.sh
```

The build requires a TeX distribution with `pdflatex`, `bibtex`, and the packages declared in the main source, including `natbib`, `tikz`, `bookmark`, `microtype`, and `lmodern`. Poppler's `pdftotext` and `pdfinfo` produce the accompanying inspection files. The script writes the PDF here and preserves compilation logs under `build/`.

The source ZIP contains every LaTeX input, the bibliography, build script, review records, and verification scripts. Compilation works after extraction without the paper archive. The paper PDFs remain in the requested repository directory `dcos/papers/salespitch`; their size and duplication make them separate from the source bundle.

## Verification

```sh
CUDA_VISIBLE_DEVICES=-1 python scripts/check_mathematics.py
python scripts/check_document.py
python scripts/render_review.py
```

The deterministic mathematics checks require NumPy. Rendering requires Pillow and Poppler. `check_document.py` additionally requires the repository layout and paper collection to verify every cited PDF. Acquisition and literature-ledger scripts retain paths to the repository's research cache; they are provenance utilities, not requirements for compiling the manuscript.

The delivered manuscript has 46 pages. All 12 bibliography entries are cited and have verified local PDFs. All 23 deterministic mathematical checks pass, and the final LaTeX and BibTeX runs have no warnings or unresolved references. Every rendered page was visually inspected. These checks establish document integrity and selected mathematical identities; they do not establish predictive accuracy, sales uplift, identified causal GDP effects, or human acceptance of the prose.

The prior proposal under `docs/salespitch/` is preserved. No client data were used, no statistical model was trained, and no GPU was accessed.
