#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build salespitch_cashflow_fx.tex > build/pass1.stdout 2>&1
bibtex build/salespitch_cashflow_fx > build/bibtex.stdout 2>&1
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build salespitch_cashflow_fx.tex > build/pass2.stdout 2>&1
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build salespitch_cashflow_fx.tex > build/pass3.stdout 2>&1
cp build/salespitch_cashflow_fx.pdf salespitch_cashflow_fx.pdf
pdftotext -layout salespitch_cashflow_fx.pdf build/salespitch_cashflow_fx.txt
pdfinfo salespitch_cashflow_fx.pdf > build/pdfinfo.txt
