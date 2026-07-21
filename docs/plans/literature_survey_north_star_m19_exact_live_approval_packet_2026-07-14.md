# M19 Exact One-Shot Live Metadata Approval Packet

Date: `2026-07-14`
Status: `FINALIZED_AND_REVIEWED_PENDING_FRESH_HUMAN_APPROVAL_DO_NOT_EXECUTE_LIVE`

## Approval Requested

Approve exactly one metadata-only execution of the command below at commit
`f06ceb72cd1bb0628b01f206f9e82697e23cb0c7`, using only the four frozen
OpenAlex/arXiv requests and limits in this packet.

This approval would not authorize source/PDF/full text, citation-frontier
expansion, credentials, private/paid services, GPU use, retries, reruns, push,
release, or scientific/product claims. The current state is
`DO_NOT_EXECUTE_LIVE` until that fresh approval is given.

## Frozen Authority And Limits

| Field | Exact value |
| --- | --- |
| Execution commit | `f06ceb72cd1bb0628b01f206f9e82697e23cb0c7` |
| Required code ancestor | `bb4300c6bce20145a7c41620b0dffb703072e755` |
| Execution tree | `2d8e364d98a85df2ba0ce59dc6ad683bf4915dc1` |
| Installed wheel | SHA-256 `6605ddeb46b15c2e0f29b23466743cf2c48db6a72eb2434019b2add22d135888` |
| Topic | `Neural Optimal Transport for generative modeling and inference` |
| Seed | `arxiv:2201.12220v3` |
| Providers | `arxiv`, then `openalex` |
| Maximum normalized records | `10` |
| Request count | Exactly `4` |
| Per-request accepted body | `2,000,000` bytes |
| Aggregate accepted body | `8,000,000` bytes |
| Request timeout | `30` seconds |
| Whole attempt | `187` seconds |
| Redirects | `0` |
| Retries/reruns | `0` |
| Proxy | Explicitly disabled; proxy variables absent and no-proxy opener used |
| Credentials | Forbidden and removed from the worker environment |
| Live output root | `docs/validation/literature_survey_m19_live_metadata_2026-07-14`, currently absent |
| Closeout-bound route manifest | SHA-256 `334c1622c9228573bf717d36e842937a19991e1676f9b88d32567be718e5e7fd` |

## Exact Requests

Every request is HTTPS `GET`, port `443`, with only the listed application
headers and zero redirect/retry behavior.

| # | Provider/kind | Host/path | Decoded query | Headers | Binding SHA-256 |
| --- | --- | --- | --- | --- | --- |
| 1 | arXiv seed | `export.arxiv.org/api/query` | `id_list=2201.12220v3`; `max_results=5`; `sortBy=relevance`; `sortOrder=descending`; `start=0` | `Accept: application/atom+xml`; fixed M19 user agent | `b39a43935f22df61fa6b7e010f0d1774406fdb839fd73e4a3e1d5d83ab7b738a` |
| 2 | arXiv topic | `export.arxiv.org/api/query` | `max_results=10`; `search_query=all:Neural Optimal Transport for generative modeling and inference`; `sortBy=relevance`; `sortOrder=descending`; `start=0` | `Accept: application/atom+xml`; fixed M19 user agent | `37676a88db4aa9412c5e23700720c917735caccd036a0db8078a8e97e3f91398` |
| 3 | OpenAlex seed | `api.openalex.org/works` | `per-page=5`; `search=arxiv:2201.12220v3`; `select=id,display_name,authorships,publication_year,doi,cited_by_count,referenced_works,ids,type,publication_date` | `Accept: application/json`; fixed M19 user agent | `f8deadf857ddd0927e883bf2f9af0bfcb29fb588c28cc440f5fe2be1674455de` |
| 4 | OpenAlex topic | `api.openalex.org/works` | `per-page=10`; `search=Neural Optimal Transport for generative modeling and inference`; same exact `select` | `Accept: application/json`; fixed M19 user agent | `c304caaac38086354e3449294383cf9988cb34694128ee1df1d4f4e200779ea1` |

The fixed user agent is `research-assistant-m19/0.1
(bounded-metadata-validation)`. Authorization, cookie, from, proxy-
authorization, referer, and API-key headers are forbidden.

## Exact Command

Run once from `/home/chakwong/research-assistant` after the preflight below:

```bash
env -i HOME=/home/chakwong PATH=/usr/bin:/bin LANG=C.UTF-8 CONDA_DEFAULT_ENV=tf-gpu GIT_OPTIONAL_LOCKS=0 CUDA_VISIBLE_DEVICES=-1 PYTHONDONTWRITEBYTECODE=1 /tmp/ra_m19_isolated_bb4300c/venv/bin/python scripts/literature_survey_m19_live_metadata_supervisor.py
```

The script accepts no arguments and writes only the fixed live output root.
The main repository at `f06ceb7` contains the same supervisor bytes as the
installed `bb4300c` wheel authority; the docs/evidence-only closeout has no
`src/`, `scripts/`, or `tests/` delta.

## Mandatory Preflight

Immediately before launch, require all of the following:

- `HEAD` exactly `f06ceb72cd1bb0628b01f206f9e82697e23cb0c7`;
- `HEAD^` exactly `bb4300c6bce20145a7c41620b0dffb703072e755`;
- live output root absent;
- protected work hashes unchanged;
- installed package origin under
  `/tmp/ra_m19_isolated_bb4300c/venv/lib/python3.11/site-packages/`;
- installed wheel hash exactly as above;
- all `89` installed `research_assistant/**` package members match the hashed
  wheel byte-for-byte under that `site-packages` root, using the following
  no-network check immediately before launch:

```bash
env -i HOME=/home/chakwong PATH=/usr/bin:/bin LANG=C.UTF-8 CUDA_VISIBLE_DEVICES=-1 PYTHONDONTWRITEBYTECODE=1 /tmp/ra_m19_isolated_bb4300c/venv/bin/python -c "import hashlib,pathlib,sys,zipfile;w=pathlib.Path('/tmp/ra_m19_isolated_bb4300c/wheelhouse/research_assistant-0.1.0-py3-none-any.whl');s=pathlib.Path('/tmp/ra_m19_isolated_bb4300c/venv/lib/python3.11/site-packages');assert hashlib.sha256(w.read_bytes()).hexdigest()=='6605ddeb46b15c2e0f29b23466743cf2c48db6a72eb2434019b2add22d135888';z=zipfile.ZipFile(w);n=sorted(x for x in z.namelist() if x.startswith('research_assistant/') and not x.endswith('/'));b=[x for x in n if not (s/x).is_file() or (s/x).read_bytes()!=z.read(x)];assert len(n)==89 and not b"
```

- installed
  `/tmp/ra_m19_isolated_bb4300c/venv/lib/python3.11/site-packages/research_assistant/survey/build.py`
  SHA-256 exactly
  `9cb782bc1f0554420dc5cf904c91b6a6dbc528a852c4ce3a8aaff4a92aba450b`;
- `src/research_assistant/survey/build.py` SHA-256
  `9cb782bc1f0554420dc5cf904c91b6a6dbc528a852c4ce3a8aaff4a92aba450b`;
- supervisor SHA-256
  `df3b16e3ce822c9b21b68bb5328929ddf5e7ed593826c5eba1f9ec56389fe641`;
- route manifest generated for `f06ceb7` hashes to the closeout-bound value;
  and
- no live M19 process or previous live result exists.

Any failed preflight means no launch and does not consume the attempt.

## One-Attempt Rule

Any launched result consumes the attempt: success, empty response, timeout,
DNS/TLS/HTTP/provider failure, boundary failure, worker failure, or partial
artifact. There is no automatic retry or result-conditioned repair. A failed
candidate does not authorize broader routes or M20.

## Result Boundary

A boundary-valid unavailable, empty, rate-limited, or provider-failed result
can answer the narrow engineering question. It cannot establish provider
reliability, metadata quality, citation recall, source/claim support,
scientific correctness, product readiness, M19 completion beyond its exact
result contract, or north-star completion.

## Approval State

Fresh human approval has not yet been given for this finalized packet.

Focused packet review round 2 returned `AGREE` after the installed-wheel
byte-replay repair.

`DO_NOT_EXECUTE_LIVE`
