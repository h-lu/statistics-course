"""Reviewed L11 registration keeps the prior L10/legacy identities intact."""
import hashlib
from pathlib import Path
from types import SimpleNamespace

from app.questions import ACTIVE_LESSONS, BANKS, CURRENT_BANKS, CURRENT_BANK_OVERRIDES, select_current_banks

ID = 'v2-l11-r3-20261018'
SHA = '97fce20fb82fe2fcbca2fe77085a67879680d17ac64256088aa24e4c07f44b54'


def test_reviewed_l11_bytes_formal_mirrors_and_identity():
    root = Path(__file__).resolve().parents[2]
    bank = BANKS[ID]
    draft = root / 'instructor-guide/knowledge-check/drafts/lesson11-20261018' / bank.path.name
    formal = root / 'instructor-guide/knowledge-check/question-bank' / bank.path.name
    assert bank.path.read_bytes() == draft.read_bytes() == formal.read_bytes()
    assert hashlib.sha256(bank.path.read_bytes()).hexdigest() == SHA
    assert bank.concept_ids == [f'l11-r3-20261018-c{i}' for i in range(1, 6)]
    assert len(bank.items) == 5
    assert bank.durations == {'attempt_a': 300, 'learn': 240, 'attempt_b': 300}
    assert BANKS['v2-l11-r1'].lesson_id == 'v2-l11-r1'
    assert BANKS['v2-l11'].lesson_id == 'v2-l11'


def test_l11_default_is_explicit_without_reinterpreting_l10():
    assert ACTIVE_LESSONS == tuple(range(1, 12))
    assert len(CURRENT_BANKS) == 11
    assert [b.lesson_id for b in CURRENT_BANKS[-2:]] == ['v2-l10-r3-20261013', ID]
    assert CURRENT_BANK_OVERRIDES == {10: 'v2-l10-r3-20261013', 11: ID}
    banks = tuple(SimpleNamespace(lesson_id=x) for x in [ID, 'v2-l11-r99', 'v2-l12-r99'])
    assert [b.lesson_id for b in select_current_banks(banks)] == [ID]
    assert select_current_banks(banks, active_lessons=(10,)) == ()


def test_l11_questions_keep_existing_equal_correctness_policy():
    for item in BANKS[ID].items:
        for phase in ['a', 'b']:
            q = item['pair'][phase]
            assert [o['id'] for o in q['options']] == list('ABCD')
            assert len({o['text'] for o in q['options']}) == 4
            assert [o['id'] for o in q['options'] if o['misconception'] is None] == [q['answer']]
            assert not {'points', 'score', 'weight'}.intersection(q)
