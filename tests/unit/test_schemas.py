from __future__ import annotations

from research_assistant.schemas.paper_record import PaperRecord


def test_paper_record_round_trip() -> None:
    rec = PaperRecord(id='p1', title='Test')
    data = rec.to_dict()
    restored = PaperRecord.from_dict(data)
    assert restored.id == 'p1'
    assert restored.title == 'Test'
