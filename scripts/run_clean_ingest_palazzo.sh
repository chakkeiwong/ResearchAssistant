#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/chakwong/research-assistant"
TMP_ROOT="/tmp/ra_clean_test"
PDF_SRC="$ROOT/local_research/papers/raw/paper_credit_risk_and_the_transmission_of_interest_rate_shocks_palazzo_20_7e82ec19.pdf"
PDF_TMP="/tmp/palazzo_test.pdf"
QUERY="Credit Risk and the Transmission of Interest Rate Shocks Palazzo"

rm -rf "$TMP_ROOT"
mkdir -p "$TMP_ROOT/local_research/papers/raw" \
         "$TMP_ROOT/local_research/papers/extracted" \
         "$TMP_ROOT/local_research/metadata" \
         "$TMP_ROOT/local_research/summaries" \
         "$TMP_ROOT/local_research/links" \
         "$TMP_ROOT/local_research/reviews" \
         "$TMP_ROOT/local_research/indices" \
         "$TMP_ROOT/local_research/caches"

cp "$PDF_SRC" "$PDF_TMP"

cd "$ROOT"
ra --root "$TMP_ROOT" ingest --pdf "$PDF_TMP" --query "$QUERY"
python - <<'PY'
import json
from pathlib import Path
meta = json.loads(Path('/tmp/ra_clean_test/local_research/metadata/paper_palazzo_test_6fe4bae4.json').read_text())
summ = json.loads(Path('/tmp/ra_clean_test/local_research/summaries/paper_palazzo_test_6fe4bae4.json').read_text())
print('parser_hints keys:', sorted((meta.get('parser_hints') or {}).keys()))
print('parser title:', (meta.get('parser_hints') or {}).get('consensus_title'))
print('summary title:', summ.get('title'))
print('summary authors:', summ.get('authors'))
print('identity_source:', summ.get('identity_source'))
print('requires_manual_review:', summ.get('requires_manual_review'))
print('provenance:', summ.get('provenance'))
PY
