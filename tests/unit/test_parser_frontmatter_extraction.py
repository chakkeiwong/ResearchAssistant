from __future__ import annotations

from research_assistant.ingest.parser_frontmatter import extract_frontmatter


def test_extract_frontmatter_joins_wrapped_title_and_authors() -> None:
    lines = [
        'A Benchmark Paper with a Long Title and Subtitle: Evidence from a Synthetic Research',
        'Workflow',
        'Carol Example and David Example and Eve Example',
        'Abstract',
        'This benchmark is designed to test parser robustness.',
        '1 Introduction',
        '2 Method',
        '3 Discussion',
    ]

    extracted = extract_frontmatter(lines)

    assert extracted.title_candidates[0] == 'A Benchmark Paper with a Long Title and Subtitle: Evidence from a Synthetic Research Workflow'
    assert extracted.authors == ['Carol Example', 'David Example', 'Eve Example']
    assert extracted.section_headings == ['Introduction', 'Method', 'Discussion']


def test_extract_frontmatter_cleans_footnote_marked_authors() -> None:
    lines = [
        '# A Benchmark Paper with Footnote-Marked Authors',
        'Frank Example† Grace Example‡',
        'Abstract',
        'This benchmark is designed to test whether parsers can recover author names without being confused by footnote markers or affiliations.',
        '1 Introduction',
        '2 Conclusion',
    ]

    extracted = extract_frontmatter(lines)

    assert extracted.title_candidates[0] == 'A Benchmark Paper with Footnote-Marked Authors'
    assert extracted.authors == ['Frank Example', 'Grace Example']
    assert extracted.section_headings == ['Introduction', 'Conclusion']
    lines = [
        'A Benchmark Paper with a Long Title and Subtitle: Evidence from a Synthetic Research Workflow',
        'Carol Example David Example Eve Example',
        'Abstract',
        'This benchmark is designed to test parser robustness.',
    ]

    extracted = extract_frontmatter(lines)

    assert extracted.authors == ['Carol Example', 'David Example', 'Eve Example']
