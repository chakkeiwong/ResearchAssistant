from __future__ import annotations

from pathlib import Path

from research_assistant.source.latex_bundle import detect_main_tex
from research_assistant.source.latex_extract import extract_latex_structure
from research_assistant.source.latex_flatten import flatten_latex_bundle


FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures' / 'latex_sources' / 'multi_file'


def test_detect_main_tex_scores_main_document() -> None:
    payload = detect_main_tex(FIXTURE)

    assert payload['main_path'].endswith('main.tex')
    assert payload['candidates'][0]['score'] > 0
    assert 'has documentclass' in payload['candidates'][0]['reasons']


def test_flatten_latex_bundle_resolves_inputs(tmp_path: Path) -> None:
    output = tmp_path / 'flattened.tex'
    report = flatten_latex_bundle(FIXTURE / 'main.tex', FIXTURE, output)

    text = output.read_text()
    assert '\\section{Method}' in text
    assert report['unresolved_includes'] == []
    assert any(path.endswith('sections/method.tex') for path in report['included_files'])


def test_extract_latex_structure_preserves_audit_evidence(tmp_path: Path) -> None:
    output = tmp_path / 'flattened.tex'
    flatten_latex_bundle(FIXTURE / 'main.tex', FIXTURE, output)

    payload = extract_latex_structure(output, source_root=FIXTURE)

    assert [section['title'] for section in payload['sections']] == ['Introduction', 'Method']
    assert 'We cite' in payload['sections'][0]['raw_latex']
    assert 'transformed target' in payload['sections'][1]['raw_latex']
    assert payload['sections'][1]['labels'] == ['sec:method', 'eq:target', 'thm:exact']
    assert len(payload['equations']) == 1
    assert payload['equations'][0]['labels'] == ['eq:target']
    assert len(payload['theorem_like_blocks']) == 1
    assert payload['theorem_like_blocks'][0]['labels'] == ['thm:exact']
    assert {label['key'] for label in payload['labels']} >= {'sec:intro', 'sec:method', 'eq:target', 'thm:exact'}
    assert payload['references'][0]['key'] == 'sec:method'
    assert payload['citations'][0]['keys'] == ['neal2011mcmc']
    assert payload['bibliography'][0]['key'] == 'neal2011mcmc'
    assert payload['macros'][0]['name'] == 'target'


def test_extract_latex_structure_handles_nested_titles_and_macro_arguments(tmp_path: Path) -> None:
    source = tmp_path / 'source.tex'
    source.write_text(r'''
\documentclass{article}
\newcommand{\pushforward}[2]{#1_{\#}#2}
\begin{document}
\section{Transport maps for $\pi(\theta)$}\label{sec:transport}
We cite \citep[Theorem 1]{neal2011mcmc,betancourt2017}.
\begin{equation}\label{eq:pushforward}
\pushforward{T}{\eta}
\end{equation}
\end{document}
''')
    (tmp_path / 'refs.bib').write_text(r'''
@article{neal2011mcmc,
  title={MCMC using Hamiltonian dynamics},
  year={2011}
}
@misc{betancourt2017,
  title={A Conceptual Introduction to Hamiltonian Monte Carlo},
  year={2017}
}
''')

    payload = extract_latex_structure(source, source_root=tmp_path)

    assert payload['sections'][0]['title'] == r'Transport maps for $\pi(\theta)$'
    assert payload['sections'][0]['labels'] == ['sec:transport', 'eq:pushforward']
    assert payload['citations'][0]['command'] == 'citep'
    assert payload['citations'][0]['keys'] == ['neal2011mcmc', 'betancourt2017']
    assert payload['macros'][0]['name'] == 'pushforward'
    assert payload['macros'][0]['arguments'] == '[2]'
    assert payload['macros'][0]['definition'] == r'#1_{\#}#2'
    assert {entry['key'] for entry in payload['bibliography']} == {'neal2011mcmc', 'betancourt2017'}
