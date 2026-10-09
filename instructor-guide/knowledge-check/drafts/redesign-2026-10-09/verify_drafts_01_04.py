#!/usr/bin/env python3
"""Read-only validation of L01-04 unpublished classroom-question drafts."""
from __future__ import annotations
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import statistics
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
RUNTIME=ROOT/'stat-check/app/question_bank/drafts/redesign-2026-10-09'


def percentile(values, probability):
    values=sorted(Fraction(v) for v in values)
    position=(len(values)-1)*Fraction(probability)
    lower=position.numerator//position.denominator
    upper=min(lower+1,len(values)-1)
    return values[lower]+(position-lower)*(values[upper]-values[lower])


def main():
    questions=0
    draft_ids=[]
    distributions={}
    for number in range(1,5):
        name=f'lesson-v2r4-{number:02d}.yml'
        content=(HERE/name).read_bytes()
        assert content==(RUNTIME/name).read_bytes(),name
        bank=json.loads(content)
        assert bank['lesson_id']==f'v2-l{number:02d}-r4'
        assert bank['duration_seconds']=={'attempt_a':300,'learn':240,'attempt_b':300}
        assert len(bank['items'])==5
        assert len({i['concept_id'] for i in bank['items']})==5
        letters=[]
        for item in bank['items']:
            assert item['title'].strip() and item['tutor_context'].strip()
            assert set(item['pair'])=={'a','b'}
            assert item['pair']['a']['prompt']!=item['pair']['b']['prompt']
            for phase in ('a','b'):
                q=item['pair'][phase]
                assert q['prompt'].strip() and q['explanation'].strip()
                assert len(q['options'])==4
                assert [o['id'] for o in q['options']]==list('ABCD')
                assert len({o['text'] for o in q['options']})==4
                correct=[o['id'] for o in q['options'] if o['misconception'] is None]
                assert correct==[q['answer']],(name,item['concept_id'],phase)
                wrong=[o['misconception'] for o in q['options'] if o['misconception'] is not None]
                assert len(wrong)==3 and len(set(wrong))==3 and all(x.strip() for x in wrong)
                assert all(letter in q['explanation'] for letter in 'ABCD')
                letters.append(q['answer']);questions+=1
        assert set(letters)==set('ABCD') and max(Counter(letters).values())<=3
        distributions[bank['lesson_id']]=dict(Counter(letters))
        draft_ids.append(bank['lesson_id'])

    # Independent arithmetic checks; the intended logical best answer and
    # distractor meaning require the teacher's content review as well.
    assert statistics.mean([6,8,10,16])==10
    assert statistics.mean([6,8,10,36])==15
    assert statistics.median([6,8,10,16])==statistics.median([6,8,10,36])==9
    assert 15-4==11 and Fraction(5,11)!=Fraction(5,15)
    assert percentile([2,6,12,20],Fraction(3,5))==Fraction(54,5)
    assert Fraction(3,2)*60==90
    assert statistics.mean([19,21])==statistics.mean([9,31])==20
    assert max([4,13])==13 and max(['4','13'])=='4'
    assert (Fraction(90,60)+4)/2==Fraction(11,4)
    assert 6+7-4==9
    assert Fraction(8,16)==Fraction(1,2) and Fraction(13,16)==Fraction(8125,10000)
    assert Fraction(8,11)>Fraction(8,16) and Fraction(8,11)<Fraction(13,16)
    original=[1,2,3,4,5,6,7,8,9,17,18]
    revised=original[:-1]+[58]
    assert Fraction(sum(revised)-sum(original),11)==Fraction(40,11)
    assert statistics.median(original)==statistics.median(revised)
    assert percentile(original,Fraction(9,10))==percentile(revised,Fraction(9,10))==17
    first=[1,3,4,8,9,11,20]
    last=first[:-1]+[80]
    assert (percentile(first,Fraction(3,4))-percentile(first,Fraction(1,4)))==(percentile(last,Fraction(3,4))-percentile(last,Fraction(1,4)))
    assert Fraction(13,5)+2*Fraction(3,20)==Fraction(13*60,300)+2*Fraction(3,20)
    assert 5+7-3==9 and Fraction(9,18)==Fraction(1,2)
    assert Fraction(4,16)==Fraction(1,4)

    archive=ROOT/'archive/redesign-2026-10-09'
    source=json.loads((archive/'source-tracked.manifest.json').read_text())['files']
    moves={r['original_path']:r['archive_path'] for r in json.loads((archive/'scope-and-restore-map.json').read_text())['moved_to_history']}
    old_checked=0
    for row in source:
        original_path=row['path']
        if original_path.endswith('.yml') and original_path.startswith(('instructor-guide/knowledge-check/question-bank/','stat-check/app/question_bank/')):
            path=ROOT/moves.get(original_path,original_path)
            data=path.read_bytes()
            assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],original_path
            old_checked+=1
    assert old_checked==174

    # Exercise the actual installed loader; do not activate the drafts.
    sys.path.insert(0,str(ROOT/'stat-check'))
    from app.questions import BANKS,CURRENT_BANKS,QuestionBank
    for number in range(1,5):
        loaded=QuestionBank(HERE/f'lesson-v2r4-{number:02d}.yml')
        assert len(loaded.items)==5
        assert loaded.lesson_id not in BANKS
    assert len(BANKS)==87
    current=[b.lesson_id for b in CURRENT_BANKS]
    assert current==[f'v2-l{n:02d}-r{4 if n==5 else 3}' for n in range(1,9)]
    print(json.dumps({'draft_lessons':draft_ids,'concepts':20,'questions':questions,
                      'byte_identical_runtime_pairs':4,'answer_distributions':distributions,
                      'numeric_relations_checked':True,'unchanged_published_yml_files':old_checked,
                      'installed_banks':len(BANKS),'current_ids_unchanged':current,
                      'draft_ids_absent_from_BANKS':True},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
