#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
mkdir -p build
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build salespitch_survey_proposal.tex >build/pass1.stdout 2>&1
bibtex build/salespitch_survey_proposal >build/bibtex.stdout 2>&1
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build salespitch_survey_proposal.tex >build/pass2.stdout 2>&1
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build salespitch_survey_proposal.tex >build/pass3.stdout 2>&1
cp build/salespitch_survey_proposal.pdf salespitch_survey_proposal.pdf
pdftotext -layout salespitch_survey_proposal.pdf build/salespitch_survey_proposal.txt
pdfinfo salespitch_survey_proposal.pdf >build/pdfinfo.txt
printf 'Built docs/salespitch/salespitch_survey_proposal.pdf\n'
