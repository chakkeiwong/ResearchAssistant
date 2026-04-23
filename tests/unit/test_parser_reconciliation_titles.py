from __future__ import annotations

from research_assistant.ingest.parser_orchestrator import reconcile_parsed_documents
from research_assistant.schemas.parsed_document import ParsedDocument


def test_reconcile_extracts_joined_title_and_authors() -> None:
    marker = ParsedDocument(
        parser_name='marker',
        body_markdown='''![](_page_0_Picture_0.jpeg)\n\n**20-05 | December 3, 2020**\n\n# **Credit Risk and the Transmission of Interest Rate Shocks**\n\n### **Berardino Palazzo**\n\n### **Ram Yamarthy**\n''',
        parse_status='ok',
    )
    markitdown = ParsedDocument(
        parser_name='markitdown',
        body_markdown='''20-05 | December 3, 2020\nCredit Risk and the Transmission of Interest\nRate Shocks\nBerardino Palazzo\nRam Yamarthy\n''',
        parse_status='ok',
    )
    rec = reconcile_parsed_documents([marker, markitdown])
    assert 'Credit Risk and the Transmission of Interest Rate Shocks' in (rec.consensus_title or '')
    assert 'Berardino Palazzo' in rec.consensus_authors
    assert 'Ram Yamarthy' in rec.consensus_authors


def test_reconcile_avoids_abstract_as_consensus_title() -> None:
    outputs = [
        ParsedDocument(
            parser_name='marker',
            title_candidates=[
                '# A Simple Test of Transport Maps for Posterior Geometry',
                'Alice Example Bob Example',
                '2026',
                '#### Abstract',
                'This synthetic benchmark paper is designed to test scholarly parser extraction of title, authors, abstract, sections, equations, and references.',
            ],
            parse_status='ok',
        ),
        ParsedDocument(
            parser_name='pdftotext',
            title_candidates=[
                'A Simple Test of Transport Maps for Posterior',
                'Geometry',
                'Alice Example',
                'Bob Example',
            ],
            parse_status='ok',
        ),
        ParsedDocument(
            parser_name='markitdown',
            title_candidates=[
                'A Simple Test of Transport Maps for Posterior',
                'Geometry',
                'Abstract',
                'This synthetic benchmark paper is designed to test scholarly parser',
            ],
            parse_status='ok',
        ),
    ]

    rec = reconcile_parsed_documents(outputs)

    assert 'A Simple Test of Transport Maps for Posterior' in (rec.consensus_title or '')
    assert 'synthetic benchmark paper is designed' not in (rec.consensus_title or '').lower()


def test_reconcile_does_not_treat_numbered_sections_as_authors() -> None:
    out = ParsedDocument(
        parser_name='markitdown',
        body_markdown='''A Simple Test of Transport Maps for Posterior Geometry\nAlice Example\nBob Example\n1 Introduction\n2 Method\n3 Experiment\n4 Conclusion\n''',
        section_headings=['1 Introduction', '2 Method', '3 Experiment', '4 Conclusion'],
        parse_status='ok',
    )

    rec = reconcile_parsed_documents([out, out])

    assert 'Alice Example' in rec.consensus_authors
    assert 'Bob Example' in rec.consensus_authors
    assert '2 Method' not in rec.consensus_authors
    assert '3 Experiment' not in rec.consensus_authors
    assert rec.consensus_section_headings == ['Introduction', 'Method', 'Experiment', 'Conclusion']


def test_reconcile_splits_joined_author_lines() -> None:
    out = ParsedDocument(
        parser_name='marker',
        body_markdown='''A Benchmark Paper with a Long Title and Subtitle: Evidence from a Synthetic Research Workflow\nCarol Example and David Example and Eve Example\n''',
        parse_status='ok',
    )

    rec = reconcile_parsed_documents([out])

    assert 'Carol Example' in rec.consensus_authors
    assert 'David Example' in rec.consensus_authors
    assert 'Eve Example' in rec.consensus_authors


def test_reconcile_ignores_abstract_plus_heading_title_leakage() -> None:
    out = ParsedDocument(
        parser_name='marker',
        title_candidates=[
            'A Benchmark Paper with Footnote-Marked Authors',
            'Frank Example Grace Example',
            '2026',
            'Abstract',
            'This benchmark is designed to test whether parsers can recover author names without being confused by footnote markers or affiliations. 1 Introduction',
        ],
        parse_status='ok',
    )

    rec = reconcile_parsed_documents([out])

    assert rec.consensus_title == 'A Benchmark Paper with Footnote-Marked Authors'
